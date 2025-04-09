import os
import shutil

from pathlib import Path

class FFmpegConstructor:
    def __init__(self, config):
        self.config = config
        self.softsub_ffmpeg_commands = {
            'init'                 : 'ffmpeg',
            'override output'      : '-y',
            'video input'          : '-i "{RAW_PATH_INPUT}"',
            'audio input'          : '-i "{SOUND_PATH_INPUT}"',
            'subtitle input'       : '-i "{SUB_PATH_INPUT}"',
            'video map'            : '-map 0:v:0',
            'audio map'            : '-map 1:a',
            'subtitle map'         : '-map 2:s',
            'garbage deleter'      : '-dn',
            'video metadata'       : '-metadata:s:v:0 title="Original" -metadata:s:v:0 language=jap',
            'audio metadata'       : '-metadata:s:a:0 title="AniBaza" -metadata:s:a:0 language=rus',
            'subtitle metadata'    : '-metadata:s:s:0 title="Caption" -metadata:s:s:0 language=rus',
            'logo burning'         : '-vf "subtitles=\'{ESCAPED_LOGO_PATH}\'"',
            'video codec'          : '-c:v {CODEC}',
            'video bitrate'        : '-b:v {BITRATE}',
            'video CRF'            : '-crf {CRF_RATE}',
            'video CQ'             : '-cq {CQ} -qmin {QMIN} -qmax {QMAX}',
            'video max bitrate'    : '-maxrate {MAX}',
            'video max bufsize'    : '-bufsize {BUFFER}',
            'render preset'        : '-preset {RENDER_PRESET}',
            'video tune'           : '-tune {TUNE}',
            'video profile'        : '-profile:v {VIDEO_PROFILE}',
            'profile level'        : '-level:v {PROFILE_LEVEL}',
            'video pixel format'   : '-pix_fmt {PIXEL_FORMAT}',
            'audio codec'          : '-c:a aac',
            'audio bitrate'        : '-b:a 320K',
            'audio discretization' : '-ar 48000',
            'subtitle codec'       : '-c:s copy',
            'video output'         : '"{OUTPUT_FILE_PATH}"'
        }
        self.hardsub_ffmpeg_commands = {
            'init'                 : 'ffmpeg',
            'override output'      : '-y',
            'video input'          : '-i "{RAW_PATH_INPUT}"',
            'audio input'          : '-i "{SOUND_PATH_INPUT}"',
            'video map'            : '-map 0:v:0',
            'audio map'            : '-map 1:a',
            'garbage deleter'      : '-dn',
            '1burning'             : '-vf "subtitles=\'{LOGO_OR_SUB_PATH}\'"',
            '2burning'             : '-vf "subtitles=\'{ESCAPED_LOGO_PATH}\', subtitles=\'{ESCAPED_SUB_PATH}\'"',
            'video codec'          : '-c:v hevc{NVENC}',
            'video bitrate'        : '-b:v {BITRATE}',
            'video CRF'            : '-crf {CRF_RATE}',
            'video CQ'             : '-cq {CQ} -qmin {QMIN} -qmax {QMAX}',
            'video max bitrate'    : '-maxrate {MAX}',
            'video max bufsize'    : '-bufsize {BUFFER}',
            'render preset'        : '-preset {RENDER_PRESET}',
            'video tune'           : '-tune {TUNE}',
            'video profile'        : '-profile:v {VIDEO_PROFILE}',
            'profile level'        : '-level:v {PROFILE_LEVEL}',
            'video pixel format'   : '-pix_fmt {PIXEL_FORMAT}',
            'audio codec'          : '-c:a aac',
            'audio bitrate'        : '-b:a 320K',
            'audio discretization' : '-ar 48000',
            'video output'         : '"{OUTPUT_FILE_PATH}"'
        }
        self.sub = {
            'name'           : '',
            'sanitized_name' : '',
            'path'           : '',
            'temp_path'      : '',
            'escaped_path'   : '',
            'exists'         : False
        }

        self.separator = f'{chr(92)}:{chr(92)}{chr(92)}'
        self.escaped_logo_path = ''

    def sub_escaper(self, path):
        self.sub['path'] = path
        self.sub['exists'] = True
        self.sub['name'] = os.path.basename(self.sub['path'])
        self.sub['sanitized_name'] = str(self.sub['name']).replace('[', '').replace(']', '')
        os.makedirs(self.config.main_paths.temp, exist_ok=True)
        self.sub['temp_path'] = os.path.join(self.config.main_paths.temp, self.sub['sanitized_name'])
        shutil.copyfile(self.sub['path'], self.sub['temp_path'])
        self.sub['escaped_path'] = f"{str(self.sub['temp_path']).replace(chr(92), '/').replace(':/', self.separator)}"

    def logo_escaper(self):
        self.escaped_logo_path = f"{str(self.config.main_paths.logo).replace(chr(92), '/').replace(':/', self.separator)}"

    def build_soft_command(self, raw_path='', sound_path='', sub_path=None,
                            output_path='', nvenc=False, crf_rate='18', cqmin='17',
                            cq='18', cqmax='25', max_bitrate='', max_buffer='', video_profile='main',
                            profile_level='4.2', pixel_format='yuv420p', preset='faster', tune='animation',
                            include_logo=True, potato_mode=False):

        os.chdir(self.config.main_paths.cwd)

        if sub_path and os.path.exists(sub_path):
            self.sub_escaper(sub_path)
        self.logo_escaper()
        command_parts = [self.softsub_ffmpeg_commands['init']]

        cmds = ['override output',
                'video input',
                'audio input',
                'subtitle input' if self.sub['exists'] else '',
                'video map',
                'audio map',
                'subtitle map' if self.sub['exists'] else '',
                'garbage deleter',
                'video metadata',
                'audio metadata',
                'subtitle metadata' if self.sub['exists'] else '',
                'logo burning' if include_logo else '',
                'video codec',
                'video CQ' if nvenc else 'video CRF',
                'video max bitrate' ,
                'video max bufsize' ,
                'render preset' ,
                'video tune' if not potato_mode else '',
                'video profile',
                'video pixel format',
                'audio codec',
                'audio bitrate',
                'audio discretization',
                'subtitle codec' if self.sub['exists'] else '',
                'video output'
            ]#'profile level',

        for command in cmds:
            if command:
                command_parts.append(self.softsub_ffmpeg_commands[command])

        command = " ".join(command_parts)
        str_out = command.format(
            RAW_PATH_INPUT    = raw_path,
            SOUND_PATH_INPUT  = sound_path,
            ESCAPED_LOGO_PATH = self.escaped_logo_path,
            CODEC             = 'libx264' if not nvenc else 'h264_nvenc',
            BITRATE           = '3500k',
            CRF_RATE          = crf_rate,
            QMIN              = cqmin,
            CQ                = cq,
            QMAX              = cqmax,
            MAX               = max_bitrate,
            BUFFER            = max_buffer,
            RENDER_PRESET     = preset,
            TUNE              = tune,
            VIDEO_PROFILE     = video_profile,
            PROFILE_LEVEL     = profile_level,
            PIXEL_FORMAT      = pixel_format,
            SUB_PATH_INPUT    = sub_path,
            OUTPUT_FILE_PATH  = output_path
        )
        self.config.logging_module.write_to_log('FFmpegConstructor', 'build_soft_command', f'FFmpeg constructor softsub: {str_out}')
        return str_out

    def build_hard_command(self, raw_path='', sound_path='', sub_path=None,
                            output_path='', nvenc=False, crf_rate='18', cqmin='17',
                            cq='18', cqmax='25', max_bitrate='', max_buffer='', preset='faster', tune='animation', video_profile='main',
                            profile_level='4.2', pixel_format='yuv420p',
                            include_logo=True, potato_mode=False):

        os.chdir(self.config.main_paths.cwd)

        if sub_path and os.path.exists(sub_path):
            self.sub_escaper(sub_path)
        self.logo_escaper()
        command_parts = [self.hardsub_ffmpeg_commands['init']]
        burning = ''
        if include_logo and self.sub['exists']:
            burning = '2burning'
        elif include_logo or self.sub['exists']:
            burning = '1burning'
        else:
            burning = ''
        cmds = ['override output',
                'video input',
                'audio input' if sound_path else '',
                'video map',
                'audio map' if sound_path else '',
                'garbage deleter',
                f"{burning}",
                'video codec',
                'video CQ' if nvenc else 'video CRF',
                'video max bitrate',
                'video max bufsize',
                'render preset',
                'video tune' if not potato_mode else '',
                'video profile',
                'video pixel format',
                'audio codec' if sound_path else '',
                'audio bitrate' if sound_path else '',
                'audio discretization' if sound_path else '',
                'video output'
            ]#'profile level',

        for command in cmds:
            if command:
                command_parts.append(self.hardsub_ffmpeg_commands[command])

        command = " ".join(command_parts)
        str_out = command.format(
            RAW_PATH_INPUT    = raw_path,
            SOUND_PATH_INPUT  = sound_path,
            ESCAPED_LOGO_PATH = self.escaped_logo_path,
            ESCAPED_SUB_PATH  = self.sub['escaped_path'],
            LOGO_OR_SUB_PATH  = self.escaped_logo_path if include_logo else self.sub['escaped_path'],
            NVENC             = '_nvenc' if nvenc else '',
            BITRATE           = '3500k',
            CRF_RATE          = crf_rate,
            QMIN              = cqmin,
            CQ                = cq,
            QMAX              = cqmax,
            MAX               = max_bitrate,
            BUFFER            = max_buffer,
            RENDER_PRESET     = preset,
            TUNE              = tune,
            VIDEO_PROFILE     = video_profile,
            PROFILE_LEVEL     = profile_level,
            PIXEL_FORMAT      = pixel_format,
            OUTPUT_FILE_PATH  = output_path
        )
        self.config.logging_module.write_to_log('FFmpegConstructor', 'build_hard_command', f'FFmpeg constructor hardsub: {str_out}')
        return str_out

    def remove_temp_sub(self):
        if os.path.exists(self.sub['temp_path']):
            os.remove(self.sub['temp_path'])
            self.sub = {
                'name' : '',
                'sanitized_name' : '',
                'path' : '',
                'temp_path' : '',
                'escaped_path' : '',
                'exists' : False
            }
