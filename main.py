from PyQt5.QtWidgets import QApplication, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QRadioButton, QVBoxLayout, \
    QLabel, QScrollArea, QPushButton, QHBoxLayout, QFileDialog
from PyQt5.QtCore import QThread, pyqtSignal
from pathlib import Path
import sys

import iperf3


def conn_check(server_ip, server_port, protocol):
    try:
        client = iperf3.Client()
        client.duration = 1
        client.server_hostname = server_ip
        client.port = server_port
        client.protocol = protocol
        result = client.run()

        if result.error:
            print(result.error)
            return str(result.error)
        else:
            print(result)
            return result
    except Exception as e:
        print("Error running iperf command:")
        print(e)
        return str(e)

class TestResultFormatter:
    def __init__(self, result):
        self.result = result

    def format_paragraph(self):
        paragraph = (
            f"iperf Test Result\n\n"
            f"Start Time: {self.result.time}\n\n"
            f"System Info: {self.result.system_info}\n\n"
            f"Version: {self.result.version}\n\n"
            f"Local Host: {self.result.local_host}, Local Port: {self.result.local_port}\n\n"
            f"Remote Host: {self.result.remote_host}, Remote Port: {self.result.remote_port}\n\n"
            f"Test Protocol: {self.result.protocol}\\nn"
            f"Number of Streams: {self.result.num_streams}\n\n"
            f"Block Size: {self.result.blksize}\n\n"
            f"Omit: {self.result.omit}\n\n"
            f"Duration: {self.result.duration} seconds\n\n"
            f"Local CPU Load: \n\tTotal {self.result.local_cpu_total}%, \n\tUser {self.result.local_cpu_user}%, \n\tSystem {self.result.local_cpu_system}%\n\n"
            f"Remote CPU Load: \n\tTotal {self.result.remote_cpu_total}%, \n\tUser {self.result.remote_cpu_user}%, \n\tSystem {self.result.remote_cpu_system}%\n\n"
        )

        if self.result.protocol == 'TCP':
            paragraph += (
                f"TCP MSS Default: {self.result.tcp_mss_default}\n\n"
                f"Retransmits: {self.result.retransmits}\n\n"
                f"Sent Bytes: {self.result.sent_bytes}, Sent Bits per Second: {self.result.sent_bps}\n\n"
                f"Received Bytes: {self.result.received_bytes}, Received Bits per Second: {self.result.received_bps}\n\n"
            )
        elif self.result.protocol == 'UDP':
            paragraph += (
                f"Bytes: {self.result.bytes}\n"
                f"Bits per Second: {self.result.bps}, Jitter (ms): {self.result.jitter_ms}\n"
                f"Kilobits per Second: {self.result.kbps}, Megabits per Second: {self.result.Mbps}\n"
                f"KiloBytes per Second: {self.result.kB_s}, MegaBytes per Second: {self.result.MB_s}\n"
                f"Packets: {self.result.packets}, Lost Packets: {self.result.lost_packets}\n"
                f"Lost Percent: {self.result.lost_percent}%\n"
                f"Seconds: {self.result.seconds}\n"
            )

        return paragraph




class WorkerThread(QThread):
    finished = pyqtSignal(str)

    def __init__(self, server_ip, server_port, protocol):
        super().__init__()
        self.server_ip = server_ip
        self.server_port = server_port
        self.protocol = protocol

    def run(self):
        result = conn_check(server_ip=self.server_ip, server_port=self.server_port, protocol=self.protocol)
        if isinstance(result, str):
            self.finished.emit(result)
        else:
            result_formatter = TestResultFormatter(result)
            formatted_paragraph = result_formatter.format_paragraph()
            self.finished.emit(formatted_paragraph)




class InputDialog(QDialog):
    def __init__(self, labels, parent=None):
        super().__init__(parent)
        self.setFixedSize(600, 400)
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        saveButton = QPushButton("Save", self)

        layout = QFormLayout(self)

        self.inputs = []
        for lab in labels:
            self.inputs.append(QLineEdit(self))
            layout.addRow(lab, self.inputs[-1])

        self.protocol_radio_tcp = QRadioButton("TCP", self)
        self.protocol_radio_udp = QRadioButton("UDP", self)
        self.protocol_radio_tcp.setChecked(True)

        protocol_layout = QVBoxLayout()
        protocol_layout.addWidget(self.protocol_radio_tcp)
        protocol_layout.addWidget(self.protocol_radio_udp)
        layout.addRow("Protocol:", protocol_layout)

        scroll_area = QScrollArea(self)
        self.result_label = QLabel(self)
        self.result_label.setWordWrap(True)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.result_label)
        layout.addRow(scroll_area)

        button_layout = QHBoxLayout()
        button_layout.addWidget(buttonBox)
        button_layout.addWidget(saveButton)
        layout.addRow(button_layout)

        buttonBox.accepted.connect(self.on_accepted)
        buttonBox.rejected.connect(self.reject)
        saveButton.clicked.connect(self.save_result)

        self.worker_thread = None

    def on_accepted(self):
        inputs = self.getInputs()
        print(inputs[0], inputs[1])

        if self.protocol_radio_tcp.isChecked():
            protocol = "TCP"
        elif self.protocol_radio_udp.isChecked():
            protocol = "UDP"
        else:
            protocol = "TCP"

        self.worker_thread = WorkerThread(server_ip=inputs[0], server_port=inputs[1], protocol=protocol)
        self.worker_thread.finished.connect(self.show_result)
        self.worker_thread.start()

        self.result_label.setText("Please wait...")

    def show_result(self, result):
        self.result_label.setText(result)

    def getInputs(self):
        server_ip = self.inputs[0].text()
        server_port = self.inputs[1].text()

        if not server_port:
            server_port = "5201"

        return server_ip, server_port

    def save_result(self):
        result_text = self.result_label.text()
        if result_text:
            downloads_path = str(Path.home() / "Downloads")
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Result", downloads_path, "Text Files (*.txt)")
            if file_path:
                with open(file_path, 'w') as file:
                    file.write(result_text)

    def closeEvent(self, event):
        if self.worker_thread is not None and self.worker_thread.isRunning():
            self.worker_thread.finished.disconnect(self.show_result)
            self.worker_thread.quit()
            self.worker_thread.wait()

        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    dialog = InputDialog(labels=["Server IP", "Server Port"])

    if dialog.exec():
        sys.exit(app.exec_())