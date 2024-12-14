import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QTableWidget, QTableWidgetItem, QPushButton, QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
import pandas as pd
import mutagen
from mutagen.id3 import TSRC
import filetype
import struct

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modyfikator Tagów ISRC")
        self.setGeometry(300, 100, 900, 750)
        self.labelState = QLabel("Nie wybrano folderu", self)
        self.labelState.setAlignment(Qt.AlignCenter)
        self.labelState.setGeometry(0, 0, 1000, 50)
        self.labelState.move(0,55)


        self.labelVersion = QLabel("Nie wybrano folderu", self)
        self.labelVersion.setAlignment(Qt.AlignCenter)
        self.labelVersion.setGeometry(0, 0, 100, 1350)
        self.labelVersion.move(0,55)
        self.labelVersion.setText('WERSJA 1.2.0')

        self.button = QPushButton("Wybierz folder", self)
        self.button.move(10, 60)
        self.button.clicked.connect(self.Read)

        self.mod_but = QPushButton("Modyfikuj", self)
        self.mod_but.setEnabled(False)
        self.mod_but.move(120, 60)
        self.mod_but.clicked.connect(self.Modyfi)


        self.image_label = QLabel(self)
        self.image_label.setGeometry(10, 110, 300, 240)
        self.table = QTableWidget(self)
        


        self.table.setGeometry(320, 110, 560, 610)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Nazwa", "Typ", "ISRC w arkuszu", "ISRC ID3 w plku", " ISRC aXML w plku   "])

    def get_chunk_data(self, file_path, chunk_id):
        with open(file_path, 'rb') as file:
            file.seek(12)  # Przesuń kursor na początek listy chunków

            while True:
                curr_chunk_id = file.read(4)
                if not curr_chunk_id:
                    break

                curr_chunk_size = struct.unpack('<I', file.read(4))[0]

                if curr_chunk_id == chunk_id.encode('ascii'):
                    chunk_data = file.read(curr_chunk_size)
                    return chunk_data

                file.seek(curr_chunk_size, 1)  # Przesuń kursor o rozmiar chunka

        return None

    def modify_axml_chunk(self, file_path, chunk_id, new_chunk_data):
        with open(file_path, 'r+b') as file:
            file.seek(12)  # Przesuń kursor na początek listy chunków

            while True:
                curr_chunk_id = file.read(4)
                if not curr_chunk_id:
                    break

                curr_chunk_size = struct.unpack('<I', file.read(4))[0]

                if curr_chunk_id == chunk_id.encode('ascii'):
                    if len(new_chunk_data) <= curr_chunk_size:
                        file.seek(-4, 1)  # Przesuń kursor o 4 bajty wstecz
                        file.write(struct.pack('<I', len(new_chunk_data)))  # Zapisz nowy rozmiar chunka
                        file.write(new_chunk_data)  # Zapisz nową zawartość chunka
                        return True
                    else:
                        print("Nowa zawartość chunka jest zbyt długa.")
                        return False

                file.seek(curr_chunk_size, 1)  # Przesuń kursor o rozmiar chunka

        return False

    def create_chunk(self, file_path, chunk_id, chunk_data):
        with open(file_path, 'r+b') as file:
            # Sprawdź czy chunk już istnieje
            # existing_chunk_data = self.get_chunk_data(file_path, chunk_id)
            # if existing_chunk_data:
            #     existing_isrc = self.extract_isrc_from_axml_chunk(existing_chunk_data)
            #     if existing_isrc != isrc:
            #         print(f"Kod ISRC w chunku '{chunk_id}': {existing_isrc}")
            #         print(f"Podmieniam na: {isrc}")
            #         new_chunk_data = self.modify_isrc_in_axml_chunk(existing_chunk_data, isrc)
            #         if new_chunk_data:
            #             self.modify_axml_chunk(file_path, chunk_id, new_chunk_data)
            #     else:
            #         print(f"Kod ISRC w chunku '{chunk_id}': {existing_isrc}")
            #     return False

            # Dodaj nagłówek RIFF, jeśli go nie ma
            file.seek(0)
            header = file.read(4)
            if header != b'RIFF':
                file.seek(0)
                file.write(b'RIFF')  # Dodaj nagłówek RIFF
                file.write(struct.pack('<I', 0))  # Aktualizacja rozmiaru pliku
                file.write(b'WAVE')

            # Przesuń kursor na koniec pliku, aby dodać nowy chunk
            file.seek(0, 2)

            file.write(chunk_id.encode('ascii'))
            file.write(struct.pack('<I', len(chunk_data)))
            file.write(chunk_data)

            # Zaktualizuj rozmiar pliku w nagłówku RIFF
            file_size = file.tell()
            file.seek(4)
            file.write(struct.pack('<I', file_size - 8))  # Odejmij 8 bajtów od rozmiaru pliku WAV

        return True

    def create_isrc_chunk(self, file_path, isrc):
        isrc_data = isrc.encode('ascii')

        chunk_id = 'ISRC'
        chunk_size = len(isrc_data)

        with open(file_path, 'r+b') as file:
            # Sprawdź czy chunk już istnieje
            existing_chunk_data = self.get_chunk_data(file_path, chunk_id)
            if existing_chunk_data:
                existing_isrc = existing_chunk_data.decode('utf-8')
                if existing_isrc != isrc:
                    print(f"Chunk '{chunk_id}' już istnieje.")
                    print(f"Kod ISRC w chunku '{chunk_id}': {existing_isrc}")
                    print(f"Podmieniam na: {isrc}")
                    self.modify_axml_chunk(file_path, chunk_id, isrc_data)
                else:
                    print(f"Kod ISRC w chunku '{chunk_id}': {existing_isrc}")
                return False

            file.seek(0, 2)  # Przesuń kursor na koniec pliku, aby dodać nowy chunk

            file.write(chunk_id.encode('ascii'))
            file.write(struct.pack('<I', chunk_size))
            file.write(isrc_data)

            # Zaktualizuj rozmiar pliku w nagłówku RIFF
            file_size = file.tell()
            file.seek(4)
            file.write(struct.pack('<I', file_size - 8))  # Odejmij 8 bajtów od rozmiaru pliku WAV

        return True

    def extract_isrc_from_axml_chunk(self, axml_chunk_data):
        start_index = axml_chunk_data.find(b'ISRC:')  # Znajdź początek pola ISRC
        if start_index != -1:
            end_index = axml_chunk_data.find(b'</dc:identifier>', start_index)  # Znajdź koniec pola ISRC
            if end_index != -1:
                isrc_field = axml_chunk_data[start_index:end_index]  # Wyodrębnij pole ISRC
                isrc = isrc_field.decode('utf-8')  # Odczytaj pełny kod ISRC
                return isrc.split(':')[-1]  # Zwróć wartość ISRC bez prefiksu

        return None

    def modify_isrc_in_axml_chunk(axml_chunk_data, new_isrc):
        start_index = axml_chunk_data.find(b'ISRC:')  # Znajdź początek pola ISRC
        if start_index != -1:
            end_index = axml_chunk_data.find(b'</dc:identifier>', start_index)  # Znajdź koniec pola ISRC
            if end_index != -1:
                new_isrc_field = b'ISRC:' + new_isrc.encode('utf-8')  # Nowe pole ISRC
                new_axml_chunk_data = axml_chunk_data[:start_index] + new_isrc_field + axml_chunk_data[end_index:]
                return new_axml_chunk_data

        return None

    def GetListCode(self, file_path, file):
        file_path = os.path.join(file_path, file)
        try:
            df = pd.read_excel(file_path, usecols=[25], skiprows=8, engine='openpyxl')
            isrc_codes = df.values.tolist()
            return isrc_codes
        except Exception as e:
            print(f"Error reading Excel file: {e}")
            return []

    def GetListName(self, file_path, file):
        file_path = os.path.join(file_path, file)
        try:
            df = pd.read_excel(file_path, usecols=[26], skiprows=8, engine='openpyxl')
            isrc_codes = df.values.tolist()
            return isrc_codes
        except Exception as e:
            print(f"Error reading Excel file: {e}")
            return []

    def Read(self):
        self.Main()

    def Modyfi(self):
        self.Main(modyfication=True)

    def Main(self, modyfication=False):
        if not modyfication: 
            self.folder_path = QFileDialog.getExistingDirectory(self, "Wybierz folder")
        files = os.listdir(self.folder_path)
        files.sort()  # Sort files by name
        zawieraWav = False
        zawieraXlsx = False
        isrcID3Zgodne = True
        isrcAxmlZgodne = True
        axmlZawiera = False

        # Clear the previous image
        self.image_label.clear()

        if self.folder_path:
            for i in reversed(range(self.table.rowCount())):
                self.table.removeRow(i)
            for i, file_name in enumerate(files):  # Use sorted file list
                # Skip hidden files created by macOS
                if file_name.startswith("._"):
                    continue

                file_type = os.path.splitext(file_name)[1]
                if file_type.lower() in [".jpg", ".jpeg", ".png", ".bmp"]:
                    pixmap = QPixmap(os.path.join(self.folder_path, file_name))
                    pixmap = pixmap.scaled(300, 240)
                    self.image_label.setPixmap(pixmap)
                elif file_type.lower() in [".wav"]:
                    zawieraWav = True
                    row_position = self.table.rowCount()
                    self.table.insertRow(row_position)
                    self.table.setItem(row_position , 0,QTableWidgetItem(file_name))
                    self.table.setItem(row_position , 1,QTableWidgetItem("Audio"))
                elif file_type.lower() == ".xlsx":
                    zawieraXlsx = True
                    row = 0
                    isrc_code = self.GetListCode(self.folder_path,file_name)
                    isrc_name = self.GetListName(self.folder_path,file_name)
                    
                    filePath = os.listdir(self.folder_path)
                    filePath.sort() # Sort files by name
                    plikiZgodne = True
                    _isrc = None
                    for files in filePath: 
                        file_path = os.path.join(self.folder_path, files)
                        if files.endswith('.wav'):
                            chunk_id = 'axml'
                            isrc = isrc_code[row][0]
                            # Sprawdź czy istnieje chunk 'axml'
                            chunk_data = self.get_chunk_data(file_path, chunk_id)
                            
                            if chunk_data:
                                _isrc = self.extract_isrc_from_axml_chunk(chunk_data)
                                if _isrc:
                                    axmlZawiera = True
                                    print(f"Kod ISRC w chunku '{chunk_id}': {_isrc}")
                                    print(_isrc,isrc)
                                    if _isrc != isrc:
                                        isrcAxmlZgodne = False
                                        print('axml ISRC niezgodne')
                                        pass
                                        # print(f"Podmieniam naaaa: {isrc}")
                                        # new_chunk_data = modify_isrc_in_axml_chunk(chunk_data, isrc)
                                        # if new_chunk_data:
                                        #     modify_axml_chunk(file_path, chunk_id, new_chunk_data)
                                    else:
                                        print('axml ISRC zgodne')
    
                                else:
                                    isrcAxmlZgodne = False
                                    print(f"Nie znaleziono kodu ISRC w chunku '{chunk_id}'.")
                            else:
                                print('axml ISRC niezgodne')
                            try:  
                                if isrc_name[row][0] in files:
                                    print('zgodność')
                                else:
                                    print('niezgodność') 
                                    self.labelState.setText('pliki audio niezgodne z informacją xlsx')
                                    self.labelState.setStyleSheet("color: red")
                                    plikiZgodne = False
                                    return   
                            except: 
                                print('niezgodność')  
                                self.labelState.setText('pliki audio niezgodne z informacją xlsx')
                                self.labelState.setStyleSheet("color: red")
                                plikiZgodne = False
                                return

                            row_position = row
                            self.table.setItem(row_position , 2,QTableWidgetItem(isrc_code[row][0]))

                            file_path = os.path.join(self.folder_path, files)

                            # Load the file with mutagen
                            wav_file = mutagen.File(file_path)

                            # Add TSRC ISRC tags with some dummy values
                            if modyfication:
                                wav_file['TSRC'] = TSRC(encoding=3, text= isrc_code[row][0])
                                wav_file.save()
                                axml_content = f'''<ebuCoreMain xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns="urn:ebu:metadata-schema:ebucore">
                                <coreMetadata>
                                    <identifier typeLabel="GUID" typeDefinition="Globally Unique Identifier" formatLabel="ISRC" formatDefinition="International Standard Recording Code" formatLink="http://www.ebu.ch/metadata/cs/ebu_IdentifierTypeCodeCS.xml#3.7">
                                        <dc:identifier>ISRC:{isrc}</dc:identifier>
                                    </identifier>
                                </coreMetadata>
                                </ebuCoreMain>'''
                                new_chunk_data = axml_content.encode('utf-8')
                                self.create_chunk(file_path, chunk_id, new_chunk_data)
                                list_chunk_data = ('INFOISRC\r\x00\x00\x00' + isrc + '\x00\x00').encode('ascii')
                                self.create_chunk(file_path, 'LIST', list_chunk_data)
                                chunk_data = self.get_chunk_data(file_path, chunk_id)
                                if chunk_data:
                                    _isrc = self.extract_isrc_from_axml_chunk(chunk_data)
                            kind = filetype.guess(os.path.join(self.folder_path, files))

                            if kind is None:
                                print('Cannot guess file type!')
                            else:
                                print('File extension: %s' % kind.extension)
                            for frame in wav_file:
                                if frame == 'TSRC':
                                    self.table.setItem(row_position , 3,QTableWidgetItem(wav_file[frame].text[0]))
                            if _isrc != None:
                                self.table.setItem(row_position , 4,QTableWidgetItem(_isrc))
                            if 'TSRC' in wav_file:
                                if not isrc_code[row][0] == wav_file[frame].text[0]:
                                    isrcID3Zgodne = False
                            else:
                                isrcID3Zgodne = False
                            row += 1
            
            if not zawieraXlsx and not zawieraWav:
                self.labelState.setText('Folder nie zawiera plików xlsx ani wave')
                self.labelState.setStyleSheet("color: red")
            elif not zawieraXlsx:
                self.labelState.setText('Folder nie zawiera pliku xlsx')
                self.labelState.setStyleSheet("color: red")
            elif not zawieraWav:
                self.labelState.setText('Folder nie zawiera plików wave')
                self.labelState.setStyleSheet("color: red")
            else:
                if (isrcID3Zgodne and isrcAxmlZgodne) or axmlZawiera:
                    if axmlZawiera and (not isrcID3Zgodne or not isrcAxmlZgodne):
                        self.labelState.setText('pliki zawierają już informację axml wybierz folder bez przypisanych kodów ISRC')
                        self.labelState.setStyleSheet("color: red")
                    else:
                        self.labelState.setText('Kody ISRC zgadzają się z kodami w xlsx')
                        self.labelState.setStyleSheet("color: green")
                    self.mod_but.setEnabled(False)
                else:
                    if plikiZgodne:
                        self.mod_but.setEnabled(True)
                    self.labelState.setText('Pliki nie zawierają kodów ISRC')
                    self.labelState.setStyleSheet("color: black")
                
app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())
