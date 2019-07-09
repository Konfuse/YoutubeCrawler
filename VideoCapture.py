import os
import sys
import socks
import socket
import dateutil.parser
import datetime

import res

from PyQt5.QtGui import QIcon
from PyQt5.QtMultimedia import QSound
from PyQt5.QtCore import QThread, pyqtSignal, QFile, QTextStream
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QComboBox, QTextBrowser, QTableWidget, \
    QTableWidgetItem, QHeaderView, QProgressBar, QHBoxLayout, QVBoxLayout, QMessageBox, QLineEdit, QLabel, \
    QAbstractItemView

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from you_get.extractors import youtube
from googletrans import Translator

DEVELOPER_KEY = ''
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'


class CrawlWindow(QWidget):
    def __init__(self):
        super(CrawlWindow, self).__init__()
        self.resize(1000, 750)
        self.setWindowTitle('视频爬取软件')
        self.setWindowIcon(QIcon(':res/maoyan.png'))

        self.start_btn = QPushButton(self)
        self.stop_btn = QPushButton(self)
        self.save_combobox = QComboBox(self)
        self.table = QTableWidget(self)
        self.log_browser = QTextBrowser(self)
        self.progressbar = QProgressBar(self)
        self.lineEdit = QLineEdit(self)
        self.pageLabel = QLabel(self)
        self.pageEdit = QLineEdit(self)

        self.input_layout = QHBoxLayout()
        self.h_layout = QHBoxLayout()
        self.v_layout = QVBoxLayout()

        self.crawl_thread = CrawlThread()
        self.btn_sound = QSound(':res/btn.wav', self)
        self.finish_sound = QSound(':res/finish.wav', self)

        self.edit_init()
        self.btn_init()
        self.combobox_init()
        self.table_init()
        self.progressbar_init()
        self.layout_init()
        self.crawl_init()

    def edit_init(self):
        self.lineEdit.setText('请输入查询关键词')
        self.lineEdit.selectAll()
        self.pageLabel.setText('页码')
        self.pageEdit.setText('请输入查询页码')
        self.pageEdit.selectAll()

    def btn_init(self):
        self.start_btn.setText('开始爬取')
        self.stop_btn.setText('停止爬取')
        self.stop_btn.setEnabled(False)

        self.start_btn.clicked.connect(lambda: self.btn_slot(self.start_btn))
        self.stop_btn.clicked.connect(lambda: self.btn_slot(self.stop_btn))

    def combobox_init(self):
        save_list = ['另存到', 'txt']
        self.save_combobox.addItems(save_list)
        self.save_combobox.setEnabled(False)

        self.save_combobox.currentTextChanged.connect(self.combobox_slot)  # 1

    def table_init(self):
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['视频名称', '视频链接', '时长'])
        # self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)

    def progressbar_init(self):
        self.progressbar.setRange(0, 100)
        self.progressbar.setValue(0)

    def layout_init(self):
        self.input_layout.addWidget(self.lineEdit)
        self.input_layout.addWidget(self.pageLabel)
        self.input_layout.addWidget(self.pageEdit)
        self.h_layout.addWidget(self.start_btn)
        self.h_layout.addWidget(self.stop_btn)
        self.h_layout.addWidget(self.save_combobox)
        self.v_layout.addWidget(self.table)
        self.v_layout.addWidget(self.log_browser)
        self.v_layout.addWidget(self.progressbar)
        self.v_layout.addLayout(self.input_layout)
        self.v_layout.addLayout(self.h_layout)
        self.setLayout(self.v_layout)

    def crawl_init(self):
        self.crawl_thread.finished_signal.connect(self.finish_slot)
        self.crawl_thread.log_signal.connect(self.set_log_slot)
        self.crawl_thread.result_signal.connect(self.set_table_slot)
        self.crawl_thread.progress_signal.connect(self.set_progress_slot)

    def btn_slot(self, btn):
        self.btn_sound.play()
        if btn == self.start_btn:
            self.log_browser.clear()
            page_number = self.pageEdit.text()
            keyword = self.lineEdit.text()
            if keyword is None or keyword == '请输入查询关键词' or not page_number.isdigit() or int(page_number) == 0:
                self.log_browser.append('<font color="red">参数错误</font>')
            else:
                self.crawl_thread.args['q'] = keyword
                self.crawl_thread.args['page_number'] = page_number
                self.log_browser.append('<font color="red">开始爬取</font>')
                self.table.clearContents()
                self.table.setRowCount(0)
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(True)
                self.save_combobox.setEnabled(False)

                self.crawl_thread.start()
        else:
            self.log_browser.append('<font color="red">停止爬取</font>')
            self.stop_btn.setEnabled(False)
            self.start_btn.setEnabled(True)
            self.save_combobox.setEnabled(True)

            self.crawl_thread.terminate()

    def finish_slot(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.save_combobox.setEnabled(True)

    def set_log_slot(self, new_log):
        self.log_browser.append(new_log)

    def set_table_slot(self, url, name, duration):
        row = self.table.rowCount()
        self.table.insertRow(row)

        self.table.setItem(row, 0, QTableWidgetItem(url))
        self.table.setItem(row, 1, QTableWidgetItem(name))
        self.table.setItem(row, 2, QTableWidgetItem(duration))

    def set_progress_slot(self, value):
        self.progressbar.setValue(value)
        if self.progressbar.value() == 100:
            self.finish_sound.play()

    def combobox_slot(self, text):
        if text == 'txt':
            self.save_to_txt()

    def save_to_txt(self):
        content = ''
        for row in range(self.table.rowCount()):
            url = '视频链接：{}\n'.format(self.table.item(row, 0).text())
            name = '视频名称：{}\n'.format(self.table.item(row, 1).text())
            duration = '时长：{}\n'.format(self.table.item(row, 2).text())
            content += url + name + duration + '\n'

        with open('./视频列表.txt', 'w', encoding='utf-8') as f:
            f.write(content)

        QMessageBox.information(self, '保存到txt', '保存成功！', QMessageBox.Ok)


class CrawlThread(QThread):
    finished_signal = pyqtSignal()
    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(str, str, str)
    progress_signal = pyqtSignal(int)
    videos_list = []
    args = {'q': 'Gaming', 'max_results': 50, 'videoDuration': 'short', 'type': 'video',
            'videoCategoryId': 20, 'page_number': '1'}

    def __init__(self):
        super(CrawlThread, self).__init__()

    def youtube_search(self, options):
        socks.setdefaultproxy(socks.PROXY_TYPE_HTTP, "127.0.0.1", 1080)
        socket.socket = socks.socksocket

        youtube_api = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                        developerKey=DEVELOPER_KEY)

        videos_id = []
        videos_result = []
        self.videos_list.clear()
        page_number = int(options['page_number'])
        pageToken = ''

        for i in range(page_number - 1):
            search_response = youtube_api.search().list(
                q=options['q'],
                part='id,snippet',
                maxResults=options['max_results'],
                type=options['type'],
                videoDuration=options['videoDuration'],
                videoCategoryId=options['videoCategoryId'],
                pageToken=pageToken
            ).execute()
            pageToken = search_response.get('nextPageToken')

        if pageToken is None:
            return 0

        for i in range(1):
            search_response = youtube_api.search().list(
                q=options['q'],
                part='id,snippet',
                maxResults=options['max_results'],
                type=options['type'],
                videoDuration=options['videoDuration'],
                videoCategoryId=options['videoCategoryId'],
                pageToken=pageToken
            ).execute()
            pageToken = search_response.get('nextPageToken')
            for search_result in search_response.get('items', []):
                if search_result['id']['kind'] == 'youtube#video':
                    videos_id.append(search_result['id']['videoId'])

            # Call the videos.list method to retrieve results matching the videoId
            video_response = youtube_api.videos().list(
                part="snippet,contentDetails,statistics",
                id=",".join(videos_id)
            ).execute()

            self.log_signal.emit('视频ID锁定完毕...')
            self.log_signal.emit('开始视频信息抓取...')
            videos_id.clear()
            videos_result.clear()
            # video_result['snippet']['publishedAt']
            for video_result in video_response.get('items', []):
                if video_result['kind'] == 'youtube#video':
                    videos_result.append(
                        [video_result['snippet']['title'], video_result['id'],
                         video_result['contentDetails']['duration']])

            for video in videos_result:
                name, url, duration = video[0], video[1], video[2]
                url = "https://www.youtube.com/watch?v=" + url
                duration = dateutil.parser.parse(duration.replace('PT', '')).strftime('%H:%M:%S')
                if '00:00:15' < duration <= '00:05:00':
                    self.result_signal.emit(name, url, duration)
                    self.videos_list.append([name, url, duration])

            self.log_signal.emit('爬取第{}页完成'.format(page_number))

        return 1

    def download(self, path):
        socks.setdefaultproxy(None)
        socket.socket = socks.socksocket
        i = 0
        for name, url, duration in self.videos_list:
            self.log_signal.emit('正在下载第{}个视频'.format(i + 1))
            i = i + 1
            try:
                youtube.download(url, merge=True, output_dir=path, caption=True)
            except Exception:
                self.log_signal.emit('An video error occurred when download:\n')
                continue

    def subtitlesTrans(self, inputFile, outputFile):
        fin = open(inputFile, 'r', encoding='utf-8')
        fout = open(outputFile, 'w', encoding='utf-8')

        translator = Translator()
        for line in fin:
            line = line.strip()
            if line:
                if line[0].isdigit():
                    fout.write(line + '\n')
                else:
                    try:
                        translations = translator.translate(line, dest='zh-cn')
                        # print(translations.origin, '->', translations.text)
                        fout.write(translations.text + '\n')
                    except Exception as e:
                        # print('translate miss..')
                        fout.write('error' + '\n')
            else:
                fout.write('\n')

        fin.close()
        fout.close()

    def clear_up(self, folder):
        origin_videos_path = os.path.join(folder, 'origin_videos')
        index = 0
        for file in os.listdir(origin_videos_path):
            info = file.split(".")
            file_name = info[0]
            file_type = info[-1]
            # print(file_name, file_type)
            if file_type == 'mp4' or file_type == 'webm':
                index = index + 1
                origin_subtitles = os.path.join(origin_videos_path, file_name + '.en.srt')
                if os.path.exists(origin_subtitles):
                    to_subtitles = os.path.join(folder, file_name.replace("'", "").replace("\"", "") + ".zh.srt")
                    self.subtitlesTrans(origin_subtitles, to_subtitles)
                    to_file = os.path.join(folder, file_name + '.mp4')
                    if os.name == 'nt':
                        to_subtitles = to_subtitles.replace('\\', '/')
                    command = 'echo N | ffmpeg -i \"%s\" -vf subtitles=\"%s\" \"%s\"' % (
                        os.path.join(origin_videos_path, file), to_subtitles, to_file
                    )
                    with os.popen(command, "r") as f:
                        # print(f.read())
                        message = f.read()
                        self.log_signal.emit('第{}个视频处理完成'.format(index))
                else:
                    to_file = os.path.join(folder, file_name + '.mp4')
                    command = 'echo N | ffmpeg -i \"%s\" \"%s\"' % (
                        os.path.join(origin_videos_path, file), to_file
                    )
                    with os.popen(command, "r") as f:
                        # print(f.read())
                        message = f.read()
                        self.log_signal.emit('第{}个视频处理完成'.format(index))

    def run(self):
        flag = 0
        try:
            flag = self.youtube_search(self.args)
        except HttpError as e:
            flag = -1
            self.log_signal.emit('<font color="red">An HTTP error %d occurred:\n%s</font>' % (e.resp.status, e.content))

        if flag == 0:
            self.log_signal.emit('<font color="red">页码超出检索上限</font>')
        elif flag == 1:
            self.log_signal.emit('<font color="red">全部链接爬取完毕，开始下载！</font>')
            self.progress_signal.emit(10)

            folder = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            if not os.path.exists(folder):
                os.mkdir(folder)
            origin_videos = os.path.join(folder, 'origin_videos')
            if not os.path.exists(origin_videos):
                os.mkdir(origin_videos)
            self.download(origin_videos)

            self.log_signal.emit('<font color="red">全部视频完毕, 开始处理视频字幕！</font>')
            self.progress_signal.emit(60)

            self.clear_up(folder)

            self.log_signal.emit('<font color="red">全部处理完毕！</font>')
            self.progress_signal.emit(100)
            self.finished_signal.emit()


def read_qss(style):
    file = QFile(style)
    file.open(QFile.ReadOnly)
    return QTextStream(file).readAll()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CrawlWindow()

    qss_style = read_qss(':res/style.qss')
    window.setStyleSheet(qss_style)

    window.show()
    sys.exit(app.exec_())
