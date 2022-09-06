from datetime import datetime
import sys
import traceback
import logging
import csv
import json
import webbrowser
from types import TracebackType
from typing import List, Optional, Type
from PyQt5 import QtCore, QtWidgets, uic
from sqlalchemy.exc import DBAPIError
from harnesslabeler import config, models, updater
from harnesslabeler.database import DBContext
from harnesslabeler.customqwidgets import ResizableMessageBox


logger = logging.getLogger("frontend")

def handle_exception(exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], exc_traceback: Optional[TracebackType]):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical("Uncaught Exception! The folowing exception was not handled.", exc_info=(exc_type, exc_value, exc_traceback))
    msg = ResizableMessageBox()
    msg.setWindowTitle("Uncaught Exception")
    msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
    msg.setText("The folowing exception was not handled. The program might need to be restarted to recover.")
    msg.setInformativeText(f"Error: {exc_type.__name__} {exc_value}")
    traceback_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    msg.setDetailedText(traceback_str)
    msg.exec()
    return


sys.excepthook = handle_exception

WIDTH, HEIGHT = 800, 1200

# TODO: Add user administration.

class LabelDialog(QtWidgets.QDialog):
    def __init__(self, parent, part_number: str, label: models.BreakoutLabel=None):
        super().__init__(parent)
        uic.loadUi('ui/labeldialog.ui', self) # Load the .ui file
        self.label = label
        if not self.label:
            self.setWindowTitle("Create Label")
        else:
            self.setWindowTitle("Edit Label")

        self.connect_signals()
        self.resize(500, 200)
        if self.label:
            self.part_number_lineEdit.setText(self.label.part_number)
            self.label_value_lineEdit.setText(self.label.value)
            if self.label.rolling_label:
                self.rolling_label_radioButton.setChecked(True)
            else:
                self.breakout_label_radioButton.setChecked(True)

        else:
            self.part_number_lineEdit.setText(part_number)
    
    def connect_signals(self) -> None:
        self.save_pushButton.clicked.connect(self.on_save_button_clicked)
        self.cancel_pushButton.clicked.connect(self.on_cancel_button_clicked)
    
    def on_cancel_button_clicked(self) -> None:
        self.reject()
        self.close()

    def on_save_button_clicked(self) -> None:
        part_number = self.part_number_lineEdit.text().strip()
        label_value = self.label_value_lineEdit.text().strip()
        rolling_label = self.rolling_label_radioButton.isChecked()
        breakout_label = self.breakout_label_radioButton.isChecked()

        if not self.label:
            self.label = models.BreakoutLabel.create(
                part_number, label_value,
                rolling_label=rolling_label
            )
        else:
            self.label.part_number = part_number
            self.label.value = label_value
            self.label.rolling_label = rolling_label
        self.accept()
        self.close()
    
    def result(self) -> models.BreakoutLabel:
        return self.label


class LoginDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        # ensure this window gets garbage-collected when closed
        # self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        uic.loadUi('ui/logindialog.ui', self) # Load the .ui file
        self.setWindowTitle(f"{config.PROGRAM_NAME} Login")
        self.user = None # type: models.User
        self.connect_signals()
        self.resize(500, 150)

        if config.LAST_USERNAME.value != "":
            self.username_lineEdit.setText(config.LAST_USERNAME.value)
            self.password_lineEdit.setFocus()
        
    
    def connect_signals(self) -> None:
        self.exit_pushButton.clicked.connect(self.on_exit_button_clicked)
        self.username_lineEdit.returnPressed.connect(self.on_login_button_clicked)
        self.password_lineEdit.returnPressed.connect(self.on_login_button_clicked)
    
    def on_exit_button_clicked(self) -> None:
        self.reject()
        self.close_and_return()

    def on_login_button_clicked(self) -> None:
        username = self.username_lineEdit.text().strip()
        password = self.password_lineEdit.text().strip()
        config.LAST_USERNAME.value = username
        config.LAST_USERNAME.save()

        if username == "" or password == "":
            QtWidgets.QMessageBox.warning(self, "Login", "Username and Password are required.")
            return

        with DBContext() as session:
            self.user = session.query(models.User).filter(models.User.username==username).first() # type: Optional[models.User]
            if not self.user or self.user and not self.user.check_password(password):
                QtWidgets.QMessageBox.warning(self, "Login", "Username and/or Password invalid.")
                self.password_lineEdit.setFocus()
                self.password_lineEdit.selectAll()
                return
            
            if not self.user.active:
                QtWidgets.QMessageBox.warning(self, "Login", "This account has been deactivated. Please try another account.")
                return
            
            session.expunge_all()
            self.accept()
            self.close_and_return()
    
    def result(self) -> models.User:
        return self.user

    def close_and_return(self):
        self.close()
        self.parent().show()


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__() # Call the inherited classes __init__ method
        uic.loadUi('ui/mainwindow.ui', self) # Load the .ui file
        self.resize(HEIGHT, WIDTH)
        self.login_dialog = None
        self.current_user = None

        self.update_window_title()

        self.connect_signals()
        self.show() # Show the GUI
        self.open_login_window()
    
    def connect_signals(self) -> None:
        self.actionLogin.triggered.connect(self.on_login)
        self.actionLogoff.triggered.connect(self.on_logoff)
        self.actionImport_Data.triggered.connect(self.import_data)
        self.actionBackup_Database.triggered.connect(self.backup_database)
        self.actionChange_Password.triggered.connect(self.open_change_password_dialog)

        self.search_pushButton.clicked.connect(self.on_search_button_clicked)
        self.show_all_radioButton.toggled.connect(self.reload_label_table)
        self.show_rolling_labels_radioButton.toggled.connect(self.reload_label_table)
        self.show_breakout_labels_radioButton.toggled.connect(self.reload_label_table)

        self.new_pushButton.clicked.connect(self.on_new_button_clicked)
        self.edit_pushButton.clicked.connect(self.on_edit_button_clicked)
        self.delete_pushButton.clicked.connect(self.on_delete_button_clicked)

        self.part_number_lineEdit.editingFinished.connect(lambda x=self.part_number_lineEdit: self.clean_text_input(x))
        self.part_number_lineEdit.returnPressed.connect(self.on_search_button_clicked)
        self.tableWidget.itemSelectionChanged.connect(self.on_label_table_item_selection_changed)
        
    def about_to_quit(self) -> None:
        logger.setLevel(logging.INFO)
        logger.info("[SYSTEM] Program closing. Preforming clean up.")
        self.on_logoff(about_to_close=True)
        
        self.current_user = None

        logger.info("[SYSTEM] Done.")
        logger.info("=" * 80)
    
    def update_window_title(self) -> None:
        logger.info("Updating main window title.")
        if self.current_user:
            self.setWindowTitle(f"{config.PROGRAM_NAME} - (v{config.PROGRAM_VERSION}) [{self.current_user}]")
            if config.DEBUG:
                self.setWindowTitle(f"{config.PROGRAM_NAME} - (v{config.PROGRAM_VERSION})  [{self.current_user}] DEBUG")
        else:
            self.setWindowTitle(f"{config.PROGRAM_NAME} - (v{config.PROGRAM_VERSION})")
            if config.DEBUG:
                self.setWindowTitle(f"{config.PROGRAM_NAME} - (v{config.PROGRAM_VERSION}) DEBUG")
    
    def on_login(self) -> None:
        if not self.current_user:
            logger.warning("No user set when running on_login.")
            return
        
        logger.info("Logging in user.")
        with DBContext() as session:
            session.add(self.current_user.on_login())
            session.commit()
            session.expunge_all()
        self.actionLogin.setEnabled(False)
        self.actionLogoff.setEnabled(True)
        self.update_window_title()
        self.show()

        if self.current_user.id != 1:
            self.actionCreate_User.setEnabled(False)
            self.actionEdit_User.setEnabled(False)
            self.actionImpart_Data.setEnabled(False)
        
        if self.current_user.id == 1 and self.current_user.check_password("admin"):
            logger.warning("For security purposes the password for this user must be changed.")
            QtWidgets.QMessageBox.information(self, "Password Change", "For security purposes the password for this user must be changed.")
            self.actionChange_Password.trigger()
    
    def on_logoff(self, about_to_close: bool=False) -> None:
        if not self.current_user:
            logger.warning("No user set when running on_logoff.")
            return
        
        logger.info("Logging off user.")
        with DBContext() as session:
            session.add(self.current_user.on_logout())
            session.commit()
            session.expunge_all()
        self.actionLogin.setEnabled(True)
        self.actionLogoff.setEnabled(False)
        self.update_window_title()
        if not about_to_close:
            self.open_login_window()
        
    def open_change_password_dialog(self) -> None:
        if not self.current_user:
            return
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Change Password")
        v_layout = QtWidgets.QVBoxLayout()
        dialog.setLayout(v_layout)
        password_lineEdit = QtWidgets.QLineEdit()
        confirm_password_lineEdit = QtWidgets.QLineEdit()
        password_lineEdit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        confirm_password_lineEdit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        password_lineEdit.editingFinished.connect(lambda x=password_lineEdit: self.clean_text_input(x))
        confirm_password_lineEdit.editingFinished.connect(lambda x=confirm_password_lineEdit: self.clean_text_input(x))
        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow(QtWidgets.QLabel("Password:"), password_lineEdit)
        form_layout.addRow(QtWidgets.QLabel("Confirm Password:"), confirm_password_lineEdit)
        v_layout.addLayout(form_layout)
        button_box =QtWidgets.QDialogButtonBox()
        button_box.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Save | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        v_layout.addWidget(button_box)

        def on_accept():
            dialog.accept()

        def on_reject():
            dialog.reject()

        button_box.accepted.connect(on_accept)
        button_box.rejected.connect(on_reject)

        result = dialog.exec()

        if result == 0:
            return
        
        password = password_lineEdit.text()
        confirm_password = confirm_password_lineEdit.text()

        logger.info(f"User '{self.current_user}' changing password.")

        if password == "" or confirm_password == "":
            logger.warning("Passwords can not be blank.")
            QtWidgets.QMessageBox.warning(self, "Error", "Passwords can not be blank.")
            return self.open_change_password_dialog()

        if password != confirm_password:
            logger.warning("Passwords do not match.")
            QtWidgets.QMessageBox.warning(self, "Error", "Passwords do not match.")
            return self.open_change_password_dialog()
        
        
        with DBContext() as session:
            user = session.query(models.User).filter(models.User.id == self.current_user.id).first() # type: models.User
            if not user:
                msg = f"Could not find current user {self.current_user}. Unable to update password."
                logger.error(msg)
                QtWidgets.QMessageBox.warning(self, "Error", msg)
                return
            user.password = password
            session.commit()
            QtWidgets.QMessageBox.information(self, "Success", "Password changed successfully.")
            return
    
    def open_login_window(self) -> None:
        self.hide()
        self.login_dialog = LoginDialog(self)
        result = self.login_dialog.exec()
        if result != 0:
            self.current_user = self.login_dialog.result()
            self.on_login()
            self.reload_label_table()
        elif result == 0:
            self.about_to_quit()
            exit(0)

    def on_search_button_clicked(self) -> None:
        logger.debug("[EVENT] Search button clicked.")
        self.reload_label_table()

    def clean_text_input(self, widget: QtWidgets.QLineEdit):
        """Strips text from widget."""
        widget.setText(widget.text().strip())
    
    def clear_label_table(self) -> None:
        logger.info("[TABLE] Clearing label table.")
        self.tableWidget.clearContents()
        self.tableWidget.setRowCount(0)
    
    def on_label_table_item_selection_changed(self) -> None:
        self.edit_pushButton.setEnabled(True)
        self.delete_pushButton.setEnabled(True)

    def get_selected_labels(self) -> Optional[List[QtWidgets.QTableWidgetItem]]:
        return self.tableWidget.selectedItems()
    
    def on_new_button_clicked(self) -> None:
        part_number = self.part_number_lineEdit.text()
        self.label_dialog = LabelDialog(self, part_number=part_number)
        result = self.label_dialog.exec()
        if result != 0:
            label = self.label_dialog.result()
            if not label:
                return
            
            with DBContext() as session:
                try:
                    session.add(label)
                    label.save(session, self.current_user)
                    session.commit()
                except DBAPIError as error:
                    logger.exception(f"Could not save new label '{label}'.")
                    msg = ResizableMessageBox()
                    msg.setWindowTitle("Exception")
                    msg.setIcon(QtWidgets.QMessageBox.Critical)
                    msg.setText(f"Could not save new label '{label}'.")
                    msg.setDetailedText(traceback.format_exc())
                    msg.exec()
                    return

            self.reload_label_table()

    def on_edit_button_clicked(self) -> None:
        items = self.get_selected_labels()
        try:
            item_id = int(items[0].text())
        except Exception as e:
            logger.exception(f"[EXCEPTION] Could not convert row ID to int. {items[0].text()}")
            msg = ResizableMessageBox()
            msg.setWindowTitle("Exception")
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText(f"Could not convert row ID to int. {items[0].text()}.")
            msg.setDetailedText(traceback.format_exc())
            msg.exec()
            return
        
        with DBContext() as session:
            label = session.query(models.BreakoutLabel).filter(models.BreakoutLabel.id == item_id).first() # type: models.BreakoutLabel
            if not label:
                logger.exception(f"Could not find label id {item_id}.")
                msg = ResizableMessageBox()
                msg.setWindowTitle("Exception")
                msg.setIcon(QtWidgets.QMessageBox.Critical)
                msg.setText(f"Could not find label id {item_id}.")
                msg.setDetailedText(traceback.format_exc())
                msg.exec()
                return
        
            self.label_dialog = LabelDialog(self, part_number=label.part_number, label=label)
            result = self.label_dialog.exec()
            if result != 0:
                label = self.label_dialog.result()
                if not label:
                    return
                
                try:
                    label.save(session, self.current_user)
                    session.commit()
                except DBAPIError as error:
                    logger.exception(f"Could not update label '{label}'.")
                    msg = ResizableMessageBox()
                    msg.setWindowTitle("Exception")
                    msg.setIcon(QtWidgets.QMessageBox.Critical)
                    msg.setText(f"Could not update label '{label}'.")
                    msg.setDetailedText(traceback.format_exc())
                    msg.exec()
                    return

            self.reload_label_table()
    
    def on_delete_button_clicked(self) -> None:
        items = self.get_selected_labels()
        try:
            item_id = int(items[0].text())
        except Exception as e:
            logger.exception(f"[EXCEPTION] Could not convert row ID to int. {items[0].text()}")
            msg = ResizableMessageBox()
            msg.setWindowTitle("Exception")
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText(f"Could not convert row ID to int. {items[0].text()}.")
            msg.setDetailedText(traceback.format_exc())
            msg.exec()
            return
        
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle("Warning")
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setText("Are you sure you want to delete this label?")
        msg.setInformativeText(f"Part number: {items[2].text()}, Label value: {items[3].text()}")
        msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel)
        msg.exec()
        if msg.result() == QtWidgets.QMessageBox.Cancel:
            return
        
        logger.info(f"Deleting label id {item_id}.")
        
        with DBContext() as session:
            label = session.query(models.BreakoutLabel).filter(models.BreakoutLabel.id == item_id).first() # type: models.BreakoutLabel
            if not label:
                logger.warning(f"Could not find label with id '{item_id}'. Selected row: [{[item.text() for item in items]}]")
                QtWidgets.QMessageBox.warning(self, "Warning", f"Could not find label with id '{item_id}'.")
                return
            
            label.delete(session, self.current_user)
        
        self.reload_label_table()

    def reload_label_table(self):
        logger.info("[SEARCH] Reloading label table.")
        self.clear_label_table()
        part_number = self.part_number_lineEdit.text()
        show_all = self.show_all_radioButton.isChecked()
        show_rolling_only = self.show_rolling_labels_radioButton.isChecked()
        show_breakout_only = self.show_breakout_labels_radioButton.isChecked()
        
        logger.debug(f"[SEARCH] Search parameters: part_number: '{part_number}', show_all: {show_all}, show_rolling_only: {show_rolling_only}, show_breakout_only: {show_breakout_only}.")

        with DBContext() as session:
            query = session.query(models.BreakoutLabel)

            if part_number != "":
                logger.info(f"[SEARCH] Applying filter 'part_number': '{part_number}'.")
                query = query.filter(models.BreakoutLabel.part_number == part_number)

            if show_rolling_only:
                logger.info(f"[SEARCH] Applying filter 'show_rolling_only'.")
                query = query.filter(models.BreakoutLabel.rolling_label == True)
            elif show_breakout_only:
                logger.info(f"[SEARCH] Applying filter 'show_breakout_only'.")
                query = query.filter(models.BreakoutLabel.rolling_label == False)
            else:
                logger.info(f"[SEARCH] Applying filter 'show_all'.")
            
            logger.debug(f"[QUERY] Query:\n{query}\n")
            # logger.debug(f"[QUERY] Parameters: {query}")
            
            labels = query.order_by(models.BreakoutLabel.part_number, models.BreakoutLabel.sort_index).all() # type: List[models.BreakoutLabel]
            logger.info(f"[SEARCH] Total labels found: {len(labels)}")

            for label in labels:
                label_id = QtWidgets.QTableWidgetItem(str(label.id))
                type_name = QtWidgets.QTableWidgetItem(label.type_name)
                part_number_value = QtWidgets.QTableWidgetItem(label.part_number)
                label_value = QtWidgets.QTableWidgetItem(label.value)
                date_modified_str = QtWidgets.QTableWidgetItem(label.date_modified_str)
                full_name = QtWidgets.QTableWidgetItem(label.modified_by_user.full_name)

                label_id.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                type_name.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                part_number_value.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                label_value.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                date_modified_str.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                full_name.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                
                self.tableWidget.insertRow(self.tableWidget.rowCount())
                self.tableWidget.setItem(self.tableWidget.rowCount() - 1, 0, label_id)
                self.tableWidget.setItem(self.tableWidget.rowCount() - 1, 1, type_name)
                self.tableWidget.setItem(self.tableWidget.rowCount() - 1, 2, part_number_value)
                self.tableWidget.setItem(self.tableWidget.rowCount() - 1, 3, label_value)
                self.tableWidget.setItem(self.tableWidget.rowCount() - 1, 4, date_modified_str)
                self.tableWidget.setItem(self.tableWidget.rowCount() - 1, 5, full_name)

        self.tableWidget.resizeColumnsToContents()
        self.edit_pushButton.setEnabled(False)
        self.delete_pushButton.setEnabled(False)
    
    def get_import_file_path(self) -> str:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open File", "/", "Supported Files (*.csv, *json)")
        return file_path
    
    def import_data(self) -> None:
        file_path = self.get_import_file_path()
        if file_path == "":
            return
        
        if file_path.endswith("csv"):
            self.import_csv(file_path)
        elif file_path.endswith("json"):
            self.import_json(file_path)
        else:
            logger.warning(f"Could not parse file: {file_path}. Extention: {file_path.split('.')[-1]} not supported.")
            QtWidgets.QMessageBox.warning(self, "Error", f"Could not parse file: {file_path}. Extention: {file_path.split('.')[-1]} not supported.")
            return

    def import_csv(self, file_path: str) -> None:
        with open(file_path, 'r') as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=',')
            for index, row in enumerate(csv_reader):
                print(row)
    
    def import_json(self, file_path: str) -> None:        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        with DBContext() as session:
            for item in data:
                label = session.query(models.BreakoutLabel)\
                        .filter(models.BreakoutLabel.part_number == item["part_number"],
                                models.BreakoutLabel.value == item["value"],
                                models.BreakoutLabel.sort_index == item["sort_index"],
                                models.BreakoutLabel.rolling_label == item["rolling_label"]).first()
                
                if not label:
                    label = models.BreakoutLabel(
                        part_number=item['part_number'],
                        value=item['value'],
                        sort_index=item['sort_index'],
                        rolling_label=True if item['rolling_label'] == "1" else False
                    )
                    session.add(label)
                    label.created_by_user_id = self.current_user.id
                    label.save(session, self.current_user)
            session.commit()
    
    def get_export_file_path(self) -> str:
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save As", f"{config.DUMPS_FOLDER}/Harness_Labeler_Database_Backup_{datetime.now().strftime('%m-%d-%Y')}", "Supported Files (*json)")
        if not file_path.endswith(".json"):
            file_path = file_path + ".json"
        return file_path
    
    def backup_database(self) -> None:
        file_path = self.get_export_file_path()
        if file_path == "":
            return
        
        logger.info("Creating database backup.")
        self.export_database(file_path)
        QtWidgets.QMessageBox.information(self, "Database Backup", "Database backup saved.")
    
    # TODO: Add database import.

    def export_database(self, file_path: str) -> None:
        logger.info("Starting database backup.")
        with DBContext() as session:

            lables = session.query(models.BreakoutLabel)\
                        .order_by(
                            models.BreakoutLabel.part_number,
                            models.BreakoutLabel.sort_index,
                            models.BreakoutLabel.rolling_label
                            ).all() # type: List[models.BreakoutLabel]
            logger.info(f"Saving {len(lables)} lables.")

            users = session.query(models.User).all() # type: List[models.User]
            logger.info(f"Saving {len(users)} users.")

            login_logs = session.query(models.UserLoginLog).all()
            logger.info(f"Saving {len(login_logs)} login logs.")

            data = {
                "labels": [label.to_dict() for label in lables],
                "users": [user.to_dict() for user in users],
                "login_logs": [login_log.to_dict() for login_log in login_logs]
            }

            with open(file_path, "w") as f:
                json.dump(data, f, indent=4)

def show_new_release_dialog(version: str, html_url: str):
    dialog = QtWidgets.QMessageBox()
    dialog.setWindowTitle("New release available")
    dialog.setText(f"New release available: {version}")
    dialog.setInformativeText("Would you like to open the download page?")
    dialog.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
    dialog.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Yes)
    dialog.setIcon(QtWidgets.QMessageBox.Icon.Information)
    if dialog.exec() == QtWidgets.QMessageBox.StandardButton.No:
        return

    # Open an internet browser to download the release
    try:
        webbrowser.open(html_url)
    except Exception as e:
        logger.exception(f"Failed to open browser to download release.")
        QtWidgets.QMessageBox.critical(None, "Error", f"Could not open browser: {e}")


def prompt_user(skip_check: bool=False):
        if not skip_check and not (config.DATABASE_USER.value == ""\
            or config.DATABASE_PASSWORD.value == ""\
            or config.DATABASE_HOST.value == ""\
            or config.DATABASE_PORT.value == ""):
            return

        logger.warning("Missing required registry key values. Prompting user to enter data.")
        
        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle("Missing Required Data")
        v_layout = QtWidgets.QVBoxLayout()
        dialog.setLayout(v_layout)
        username_lineEdit = QtWidgets.QLineEdit()
        password_lineEdit = QtWidgets.QLineEdit()
        host_lineEdit = QtWidgets.QLineEdit()
        port_spinBox = QtWidgets.QSpinBox()

        password_lineEdit.setEchoMode(QtWidgets.QLineEdit.EchoMode.PasswordEchoOnEdit)
        port_spinBox.setButtonSymbols(QtWidgets.QSpinBox.ButtonSymbols.NoButtons)
        port_spinBox.setMinimum(1024)
        port_spinBox.setMaximum(65535)

        username_lineEdit.editingFinished.connect(lambda: username_lineEdit.setText(username_lineEdit.text().strip()))
        password_lineEdit.editingFinished.connect(lambda: password_lineEdit.setText(password_lineEdit.text().strip()))
        host_lineEdit.editingFinished.connect(lambda: host_lineEdit.setText(host_lineEdit.text().strip()))

        info_label = QtWidgets.QLabel(f"Please fill in the missing MySQL database authentication info.\n\nAll settings are stored in the registry at: '{config.DATABASE_USER.base_hive_location}'")

        v_layout.addWidget(info_label)
        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow(QtWidgets.QLabel("Username:"), username_lineEdit)
        form_layout.addRow(QtWidgets.QLabel("Password:"), password_lineEdit)
        form_layout.addRow(QtWidgets.QLabel("Host:"), host_lineEdit)
        form_layout.addRow(QtWidgets.QLabel("Port:"), port_spinBox)
        v_layout.addSpacing(10)
        v_layout.addLayout(form_layout)
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Save | QtWidgets.QDialogButtonBox.StandardButton.Close)
        v_layout.addWidget(button_box)

        username_lineEdit.setText(config.DATABASE_USER.value)
        password_lineEdit.setText(config.DATABASE_PASSWORD.value)
        host_lineEdit.setText(config.DATABASE_HOST.value)
        port_spinBox.setValue(int(config.DATABASE_PORT.value))

        def on_accept():
            config.DATABASE_USER.value = username_lineEdit.text()
            config.DATABASE_PASSWORD.value = password_lineEdit.text()
            config.DATABASE_HOST.value = host_lineEdit.text()
            config.DATABASE_PORT.value = str(port_spinBox.text())

            config.DATABASE_USER.save()
            config.DATABASE_PASSWORD.save()
            config.DATABASE_HOST.save()
            config.DATABASE_PORT.save()

            if config.DATABASE_USER.value == ""\
                or config.DATABASE_PASSWORD.value == ""\
                or config.DATABASE_HOST.value == ""\
                or config.DATABASE_PORT.value == "":
                QtWidgets.QMessageBox.warning(dialog, "Warning", "Please fill in all blank fields.")
                return

            dialog.accept()

        def on_reject():
            dialog.reject()

        button_box.accepted.connect(on_accept)
        button_box.rejected.connect(on_reject)

        result = dialog.exec()
        if result == 0:
            logger.warning("User did not set missing required database info. The program can not continue.")
            QtWidgets.QMessageBox.warning(dialog, "Error", "Missing required database info. The program can not continue.")
            exit(0)
        else:
            logger.info("Missing required database info saved. Application restart required to apply changes.")
            QtWidgets.QMessageBox.warning(dialog, "Error", "Missing required database info saved. Application restart required to apply changes.\n\nProgram will close after this dialog closes.")
            exit(0)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv) # Create an instance of QtWidgets.QApplication

    newer, version, url = updater.check_for_updates()
    if newer:
        show_new_release_dialog(version, url)

    prompt_user()

    try:
        models.create_database()
    except Exception as error:
        logger.exception("Could not create database.")
        QtWidgets.QMessageBox.warning(None, "Error", "There was an issue connecting to the database. Check database authentication settings.")
        prompt_user(skip_check=True)
        exit(0)
        
    window = Ui() # Create an instance of our class
    app.aboutToQuit.connect(window.about_to_quit)
    app.exec() # Start the application