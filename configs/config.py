import os
import sys
import platform

from dataclasses import dataclass
from pathlib import Path
from modules.LoggingModule import LoggingModule

@dataclass
class Paths:
    appdata: Path
    cwd: Path
    config_dir: Path
    config: Path
    version: Path
    logs: Path
    temp: Path
    softsub: Path
    hardsub: Path
    logo: Path

    def __init__(self, cwd: str):
        self.appdata = Path(os.getenv('APPDATA') or '')
        self.cwd = Path(cwd)
        self.config_dir = Path(cwd, 'configs')
        self.config = Path(self.config_dir, 'config.ini')
        self.version = Path(self.config_dir, 'current_version.ini')
        self.logs = Path(cwd, 'logs')
        self.temp = Path(cwd, 'tmp')
        self.softsub = Path('')
        self.hardsub = Path(cwd, 'HARDSUB')
        self.logo = Path(cwd, 'logo/AniBaza_Logo16x9.ass')
        self.create_missing_folders()

    def create_missing_folders(self):
        for dir in [self.config_dir, self.logs, self.temp, self.hardsub]:
            if not os.path.exists(dir):
                os.mkdir(dir)

class Config:
    def __init__(self, paths: Paths):
        # Main paths
        self.main_paths: Paths = paths

        # Main objects
        self.logging_module = LoggingModule()
        self.command_constructor = None
        self.updater_thread = None
        self.download_thread = None
        self.ffmpeg_thread = None

        # Application info
        self.app_info = {
            'title'          : '',
            'version_number' : '',
            'version_name'   : '',
            'author'         : '',
            'update_link'    : 'https://raw.githubusercontent.com/Miki-san/AniBaza_Converter/master/latest_version.json'
        }

        # Special settings
        self.dev_settings = {
            'dev_mode' : True,
            'logging'  : {
                'state'    : True,
                'max_logs' : 10
            }
        }

        # Rendering paths
        self.rendering_paths = {
            'raw'     : '',
            'audio'   : '',
            'sub'     : '',
            'softsub' : '',
            'hardsub' : ''
        }

        # Working variables
        self.build_states = {
            'Софт и хард'      : 0,
            'Только софт'      : 1,
            'Только хард'      : 2,
            'Для хардсабберов' : 3,
            'Починить равку'   : 4
        }

        self.render_speed = {
            -1 : ('ultrafast', 'p1'),
            0  : ('superfast', 'p2'),
            1  : ('veryfast', 'p3'),
            2  : ('faster', 'p4'),
            3  : ('fast', 'p5')
        }

        self.update_search = True
        self.total_duration_sec = 0
        self.total_frames = 0
        self.current_state = ''
        self.video_res = ''
        self.first_show = True
        self.potato_PC = False

        # Build settings
        self.build_settings = {
            'episode_name'     : '',
            'build_state'      : 0,
            'logo_state'       : 0,
            'nvenc_state'      : 0,
            'softsub_settings' : {
                'video_tune'    : 'animation',
                'video_profile' : 'high10',
                'profile_level' : '4.1',
                'pixel_format'  : 'yuv420p10le'
            },
            'hardsub_settings' : {
                'video_tune'    : 'animation',
                'video_profile' : 'main10',
                'profile_level' : '4.1',
                'pixel_format'  : 'yuv420p10le'
            }
        }

    def start_log(self):
        self.logging_module.start_logging(
            self.dev_settings['logging']['state'],
            self.main_paths.logs,
            self.dev_settings['logging']['max_logs']
        )

    def log(self, module, function, message):
        # Упрощённый метод для логирования.
        self.logging_module.write_to_log(module, function, message)

    def stop_log(self):
        self.logging_module.stop_logging()

@dataclass()
class PCInfo:
    Platform: str = sys.platform
    OSName: str = ''
    OSVersion: str = ''
    CPU: str = ''
    RAM: str = ''
    GPU: str = ''

    def __post_init__(self):
        if self.is_windows():
            self._init_win32()
        else:
            self._init_default()

    def _init_win32(self):
        import wmi
        hardware = wmi.WMI()
        os_info = hardware.Win32_OperatingSystem()[0]
        proc_info = hardware.Win32_Processor()[0]
        gpu_info = hardware.Win32_VideoController()[0]

        os_name = os_info.Name.encode('utf-8').split(b'|')[0].decode('utf-8')
        os_version = ' '.join([os_info.Version, os_info.BuildNumber])
        system_ram = int(float(os_info.TotalVisibleMemorySize) // (1024 * 1024)) + 1  # KB to GB

        self.OSName = os_name
        self.OSVersion = os_version
        self.CPU = proc_info.Name
        self.RAM = str(system_ram)
        self.GPU = gpu_info.Name

    def _init_default(self):
        self.OSName = platform.system()
        self.OSVersion = platform.platform()
        self.CPU = platform.processor()

    def is_windows(self) -> bool:
        return self.Platform == 'win32'
