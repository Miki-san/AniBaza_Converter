import os
import re
import subprocess
import sys
import traceback
import requests

from PyQt5.QtWidgets import QMessageBox,QProgressDialog, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal, QThread

from threads.DownloaderThread import DownloadThread
from threads.FFmpegInstallThread import FFmpegInstallThread


class UpdaterThread(QThread):
    app_update_signal = pyqtSignal(str, str, str)
    ffmpeg_update_signal = pyqtSignal(str, str)
    error_signal    = pyqtSignal(Exception)

    def __init__(self, config):
        super().__init__()
        sys.excepthook = self.handle_exception
        self.config = config

    def handle_exception(self, e):
        error_message = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        self.config.log('AppUpdater', 'handle_exception', f"UpdaterThread Exception: {error_message}")
        self.error_signal.emit(e)

    def run(self):
        try:
            self.config.log('AppUpdater', 'run', "Running updater...")

            self.config.log('AppUpdater', 'run', "Checking for app updates...")
            app_latest_version, download_url, name = self.check_for_app_update()
            if app_latest_version:
                self.app_update_signal.emit(app_latest_version, download_url, name)
            else:
                self.config.log('AppUpdater', 'run', "Checking for ffmpeg updates...")
                ffmpeg_need_to_update, ffmpeg_latest_version, ffmpeg_installed_version = self.should_update_ffmpeg()
                if ffmpeg_need_to_update:
                    self.ffmpeg_update_signal.emit(ffmpeg_latest_version, ffmpeg_installed_version)

        except Exception as e:
            self.handle_exception(e)

    def get_latest_ffmpeg_version(self):
        try:
            url = "https://www.gyan.dev/ffmpeg/builds/release-version"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            self.config.log('AppUpdater', 'get_latest_ffmpeg_version', f"GYAN response: {response.text}")
            # Регулярное выражение для поиска версии (например, 4.3.1)
            match = re.search(r'([0-9]+\.[0-9]+(?:\.[0-9]+)?)', response.text)

            # Логирование актуальной версии
            self.config.log('AppUpdater', 'get_latest_ffmpeg_version', f"Latest FFmpeg version: {match.group(1) if match else None}")
            return match.group(1) if match else None
        except Exception as e:
            self.handle_exception(e)
        return None

    def should_update_ffmpeg(self):
        installed_version = self.config.ffmpeg.version or '0.0'
        self.config.log('AppUpdater', 'get_installed_ffmpeg_version', f"Installed FFmpeg version: {installed_version}")
        latest_version = self.get_latest_ffmpeg_version()
        if latest_version and installed_version and latest_version > installed_version:
            return True, latest_version, installed_version
        return False, None, None

    def check_for_app_update(self):
        try:
            self.config.log('AppUpdater', 'check_for_app_update', "Checking for updates...")
            response = requests.get(self.config.app_info['update_link'], timeout=5)
            response.raise_for_status()
            data = response.json()
            self.config.log('AppUpdater', 'check_for_app_update', f"Data found: {data}")
            latest_version = data.get("version")
            download_url = data.get("url")
            name = data.get("name")
            if latest_version and download_url and name and latest_version > self.config.app_info['version_number']:
                return latest_version, download_url, name
        except Exception as e:
            self.handle_exception(e)
        return None, None, None

class UpdaterUI:
    def __init__(self, main_window, config):
        self.main_window = main_window
        self.config = config

    def start_updater(self):
        self.config.log('AppUpdater', 'start_updater', "Starting updater...")
        self.config.updater_thread = UpdaterThread(self.config)
        self.config.updater_thread.app_update_signal.connect(self.show_app_update_dialog)
        self.config.updater_thread.ffmpeg_update_signal.connect(self.show_ffmpeg_update_dialog)
        self.config.updater_thread.error_signal.connect(self.show_error_dialog)
        self.config.updater_thread.start()

    def universal_message_box(self, icon, title, text, infotext, buttons, log_message=None):
        self.config.log('AppUpdater', 'universal_message_box', log_message) if log_message else None
        msg_box = QMessageBox()
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setInformativeText(infotext)
        msg_box.setStandardButtons(buttons)
        return msg_box.exec()

    def cancel_app_download(self):
        if hasattr(self.config, 'download_thread'):
            self.config.log('AppUpdater', 'cancel_app_download', "Download canceled.")
            self.config.download_thread.cancel()  # type: ignore # Останавливаем скачивание
            self.progress.close()  # Закрываем прогресс-диалог

    def app_update_progress(self, value):
        self.progress.setValue(value)
        if self.progress.wasCanceled():  # Проверка на отмену скачивания
            self.config.log('AppUpdater', 'app_update_progress', "Download canceled.")
            self.cancel_app_download()  # Останавливаем скачивание, без передачи 'canceled'

    def app_download_finished(self, path):
        self.config.log('AppUpdater', 'app_download_finished', f"Download complete: {path}")
        if path:  # Если путь не пустой
            self.progress.close()  # Закрываем прогресс-диалог
            self.config.log('AppUpdater', 'app_download_finished', "Starting installer...")
            subprocess.Popen([path], shell=True)
            self.main_window.close()

    def start_app_download(self, url, version):
        self.config.log('AppUpdater', 'start_app_download', 'Starting download...')
        self.progress = QProgressDialog(
            f"Скачиваю обновление...\n{self.config.app_info['version_number']} -> {version}",
            "Отмена",
            0, 100,
            self.main_window
        )
        self.progress.setWindowTitle("ABCUpdater")
        self.progress.setWindowFlags(self.progress.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint) # type: ignore
        self.progress.setMinimumWidth(350)
        self.progress.setWindowModality(Qt.WindowModality.ApplicationModal)

        self.cancel_button = QPushButton('Отмена', self.progress)
        self.cancel_button.clicked.connect(self.cancel_app_download)
        self.progress.setCancelButton(self.cancel_button)
        self.progress.show()
        temp_dir = os.getenv("TEMP")
        if temp_dir is None:
            raise EnvironmentError("TEMP environment variable is not set")
        installer_path = os.path.join(temp_dir, "update_installer.exe")
        self.config.download_thread = DownloadThread(self.config, url, installer_path)
        self.config.download_thread.progress_signal.connect(self.app_update_progress)
        self.config.download_thread.finished_signal.connect(self.app_download_finished)
        self.config.download_thread.error_signal.connect(self.show_error_dialog)
        self.config.download_thread.start()

    def cancel_ffmpeg_installation(self):
        if hasattr(self.config, "ffmpeg_thread"):
            self.config.ffmpeg_thread.cancel()

    def ffmpeg_install_finished(self, success):
        if hasattr(self, 'progress') and self.progress is not None:
            self.progress.close()
        if success:
            QMessageBox.information(self.main_window, "Установка завершена", "FFmpeg успешно установлен!")
        else:
            QMessageBox.warning(self.main_window, "Отмена", "Установка FFmpeg была отменена.")

    def start_ffmpeg_installation(self):
        self.config.log('AppUpdater', 'start_ffmpeg_installation', "Starting FFmpeg installation...")
        self.progress = QProgressDialog(
            "Устанавливаю FFmpeg...",
            "Отмена",
            0, 0,
            self.main_window
        )
        self.progress.setWindowTitle("FFmpeg Установка")
        self.progress.setWindowFlags(self.progress.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)  # type: ignore
        self.progress.setMinimumWidth(350)
        self.progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.cancel_button = QPushButton('Отмена', self.progress)
        self.cancel_button.clicked.connect(self.cancel_ffmpeg_installation)
        self.progress.setCancelButton(self.cancel_button)
        self.config.ffmpeg_thread = FFmpegInstallThread(self.config)
        self.config.ffmpeg_thread.progress_signal.connect(lambda msg: self.progress.setLabelText(msg))
        self.config.ffmpeg_thread.finished_signal.connect(self.ffmpeg_install_finished)
        self.config.ffmpeg_thread.error_signal.connect(self.show_error_dialog)
        self.config.ffmpeg_thread.start()
        self.progress.show()

    def show_app_update_dialog(self, latest_version, download_url, name):
        result = self.universal_message_box(
            QMessageBox.Icon.Information,
            "ABCUpdater",
            f"Доступна новая версия AniBaza Converter: {self.config.app_info['version_number']} -> {latest_version}!",
            "Вы хотите скачать и установить новую версию?",
            QMessageBox.StandardButtons(QMessageBox.StandardButton.Yes) | QMessageBox.StandardButtons(QMessageBox.StandardButton.No),
            'Showing App update dialog...'
        )
        self.config.log('AppUpdater', 'show_app_update_dialog', f"User chose to update: {result == QMessageBox.StandardButton.Yes}")
        if result == QMessageBox.StandardButton.Yes:
            self.start_app_download(download_url, latest_version)

    def show_ffmpeg_update_dialog(self, latest_version, installed_version):
        buttons = QMessageBox.StandardButtons(QMessageBox.StandardButton.Yes) | QMessageBox.StandardButtons(QMessageBox.StandardButton.No)
        message = "Вы хотите скачать и установить новую версию?"

        if not self.config.pc_info.is_windows():
            message = "Пожалуйста, обновите FFmpeg самостоятельно"
            buttons = QMessageBox.StandardButtons(QMessageBox.StandardButton.Ok)

        result = self.universal_message_box(
            QMessageBox.Icon.Information,
            "FFmpegUpdater",
            f"Доступна новая версия FFmpeg: {installed_version} -> {latest_version}!",
            message,
            buttons,
            "Необходимо обновление FFmpeg!"
        )
        self.config.log('AppUpdater', 'show_ffmpeg_update_dialog', f"User chose to update: {result == QMessageBox.StandardButton.Yes}")
        if result == QMessageBox.StandardButton.Yes:
            self.start_ffmpeg_installation()

    def show_error_dialog(self, ex):
        self.universal_message_box(
            QMessageBox.Icon.Warning,
            "ABCUpdater Error",
            "Произошла ошибка поиска или установки обновления! Повторите попытку обновления позже.",
            f"ERROR: [{type(ex)}]",
            QMessageBox.StandardButton.Yes,
            'Showing error dialog...'
        )
