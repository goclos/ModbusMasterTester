import tkinter
from tkinter import ttk
from tkinter import messagebox
import tkinter.scrolledtext as txt
from tkinter.font import Font
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.client.sync import ModbusSerialClient as ModbusSerialClient
import threading
import logging
import sys
import os
import serial.tools.list_ports
import traceback


class RedirectText(object):
    def __init__(self, text_ctrl):
        self.output = text_ctrl

    def flush(self):
        return

    def write(self, string):
        listaLinii = string.split('\n')
        filtrZakazany = ['Running transaction','Running transaction',\
                        'Changing state','New Transaction state',\
                        'Getting Frame','Factory Response','Frame advanced',\
                        'Adding transaction','Getting transaction',\
                        'Changing transaction state','Current transaction state',"Processing"]
        for elem in listaLinii: #odfiltrowanie niepotrzebnych logow
            marker=False
            for item in filtrZakazany:
                if item in elem:
                    marker = True
            if not marker:
                if not elem=="":
                    self.output.insert(tkinter.END, elem+"\n")

class GUI:
    def __init__(self, window, ports, bgColor, kolorLabelek):
        sys.stdout = self          # Set stdout here
        odstepyX = 15
        odstepyY = 5
        self.kodyFunkcji = ('01-Read coils','02-Read Discrete Inputs','03-Read holding Registers',\
                            '04-Read input Registers','05-Write output coil','06-Write holding register',\
                            '15-Write output coils','16-Write output registers')
        self.error_definition = {1:"Illegal Function",2:"illegal Data address",3:"Illegal data ValueError",\
                                4:"Slave device failure",5:"Acknowledge",6:"Slave Device busy",\
                                7:"Negative Acknowledge",8:"Memory Parity  error",10:"Gateway path unavailable",\
                                11:"Gateway Target device failed to respond"}
        self.polaRejestow = {}
        self.labelkiRejestrow = {}
        self.client = 0
        self.timer = 0
        self.kolorLabelek = kolorLabelek
        self.fontLabelek = ("Arial", 11)
        self.stop_event = threading.Event() #Definiowanie zdarzenia aby móc zatrzymać wątek wysyłania zapytań
        self.Fmain = tkinter.Frame(window, borderwidth = 2,relief="groove", bg=bgColor)
        self.Fmain.pack(pady=10, padx=10)
        self.ModbusRadioButtons = tkinter.Frame(self.Fmain,borderwidth = 2,relief="groove", bg=bgColor)
        self.f1 = tkinter.Frame(self.Fmain,  borderwidth = 2,relief="groove", bg=bgColor)   # Ustawienia ogolne Modbus
        self.ModbusTCPsettings = tkinter.Frame(self.Fmain,borderwidth = 2,relief="groove", bg=bgColor)
        self.ModbusRTUsetings = tkinter.Frame(self.Fmain,borderwidth = 2,relief="groove", bg=bgColor)   # Ustawienia Modbus RTU
        self.f3 = tkinter.Frame(self.Fmain,bg=bgColor)      # Ramka z rejestrami w zakładce pierwszej
        self.f4 = tkinter.Frame(self.Fmain,bg=bgColor)       #statystyki
        self.f5 = tkinter.Frame(self.Fmain,bg=bgColor)         #konsola tx/rx
        #Pakowanie
        self.ModbusRadioButtons.grid(row=0,column=0,columnspan=4,pady=10)
        self.ModbusTCPsettings.grid(row=1,column=0,columnspan=4)
        #self.ModbusRTUsetings.grid(row=1,column=0,columnspan=4,pady=20)
        self.f1.grid(row=2,column=0,columnspan=4,pady=20)
        self.f3.grid(row=3,column=0,columnspan=4)    #Ramka z rejestrami
        self.f4.grid(row=4,column=0,columnspan=4)    #Ramka ze statystykami
        self.f5.grid(row=5,column=0,columnspan=4)   #Ramka z logiem

        #create a pulldown menu, and add it to the menu bar
        menubar = tkinter.Menu(window)
        filemenu = tkinter.Menu(menubar, tearoff=0)
        filemenu.add_command(label="About", command=self.about)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=window.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        window.config(menu=menubar)

        self.ModbusMode = tkinter.IntVar()
        self.ModbusTCPradio = tkinter.Radiobutton(self.ModbusRadioButtons, \
                                text="Modbus TCP", variable=self.ModbusMode, \
                                value=1, command = self.ModbusChange,bg=bgColor,\
                                font=self.fontLabelek, fg=self.kolorLabelek,\
                                activebackground=bgColor,activeforeground=self.kolorLabelek,\
                                selectcolor=bgColor)
        self.ModbusTCPradio.grid(row=0, column=0)
        self.ModbusRTUradio = tkinter.Radiobutton(self.ModbusRadioButtons, \
                                text="Modbus RTU", variable=self.ModbusMode,\
                                value=2, command = self.ModbusChange,bg=bgColor,\
                                font=self.fontLabelek, fg=self.kolorLabelek,\
                                activebackground=bgColor,activeforeground=self.kolorLabelek,\
                                selectcolor=bgColor)
        self.ModbusRTUradio.grid(row=0, column=1)
        self.ModbusRTUradio.select()
        self.ModbusTCPradio.select()


        #Adres IP
        labelkaIP = tkinter.Label(self.ModbusTCPsettings, text="IP address:", bg=bgColor, font=self.fontLabelek, fg=self.kolorLabelek)
        #labelkaIP.configure(font=fontLabelek)
        labelkaIP.grid(row=1, column=0, padx = odstepyX)
        self.IPaddress = tkinter.Entry(self.ModbusTCPsettings, width=15, relief='sunken', borderwidth=3)
        self.IPaddress.grid(row=1, column=1,padx = 5)
        self.IPaddress.insert(0, "127.0.0.1")
        #Port TCP
        tkinter.Label(self.ModbusTCPsettings, text="TCP port:",bg=bgColor,font=self.fontLabelek, fg=self.kolorLabelek).grid(row=1, column=2)
        self.TCPport = tkinter.Entry(self.ModbusTCPsettings, relief='sunken', borderwidth=3)
        self.TCPport.grid(row=1, column=3,padx = odstepyX, pady=odstepyY)
        self.TCPport.insert(0, "502")
        #Server ID
        tkinter.Label(self.f1, text="Server / Slave ID:",bg=bgColor,font=self.fontLabelek, fg=self.kolorLabelek).grid(row=2, column=0)
        self.serverID = tkinter.Entry(self.f1,width=15, relief='sunken', borderwidth=3)
        self.serverID.grid(row=2, column=1,padx = odstepyX , pady=odstepyY)
        self.serverID.insert(0, "1")
        #Function code
        tkinter.Label(self.f1, text="Function code:",bg=bgColor,font=self.fontLabelek, fg=self.kolorLabelek).grid(row=2, column=2)
        self.FuncCode = ttk.Combobox(self.f1, values = self.kodyFunkcji,state="readonly") # tworzenie kontrolki Combobox
        self.FuncCode.bind('<<ComboboxSelected>>', self.on_select_changed)
        self.FuncCode.grid(row=2, column=3) # umieszczenie kontrolki na oknie głównym
        self.FuncCode.current(0) # ustawienie domyślnego indeksu zaznaczenia
        #Start address
        tkinter.Label(self.f1, text="Start address (dec):",bg=bgColor,font=self.fontLabelek, fg=self.kolorLabelek).grid(row=3, column=0)
        self.startadres = tkinter.Entry(self.f1,width=15, relief='sunken', borderwidth=3)
        self.startadres.grid(row=3, column=1,padx = odstepyX, pady=odstepyY )
        self.startadres.insert(0, "0")
        #register count
        tkinter.Label(self.f1, text="Register count:",bg=bgColor,font=self.fontLabelek, fg=self.kolorLabelek).grid(row=4, column=0)
        self.regCount = tkinter.Entry(self.f1,width=15, relief='sunken', borderwidth=3)
        self.regCount.grid(row=4, column=1,padx = odstepyX, pady=odstepyY )
        self.regCount.insert(0, "1")
        #Pool interval
        tkinter.Label(self.f1, text="Poll interval (ms):",bg=bgColor,font=self.fontLabelek, fg=self.kolorLabelek).grid(row=3, column=2)
        self.poolInterval = tkinter.Entry(self.f1, relief='sunken', borderwidth=3)
        self.poolInterval.grid(row=3, column=3,padx = odstepyX , pady=odstepyY)
        self.poolInterval.insert(0, "500")
        #Przyciski Start stop
        self.connect = tkinter.Button(self.f1, text = "Connect", height=2, width=10, command=self.tcpConnect)
        self.connect.grid(row=5, column=0, pady=20, padx=30)
        self.start = tkinter.Button(self.f1, text = "Start", height=2, width=10, command=self.startSending, state='disabled')
        self.start.grid(row=5, column=1)
        self.stop = tkinter.Button(self.f1, text = "Stop", height=2,width=10, command=self.stopSending, state='disabled')
        self.stop.grid(row=5, column=2)
        self.disco = tkinter.Button(self.f1, text = "Disconnect", height=2, width=10, command=self.tcpClose, state='disabled')
        self.disco.grid(row=5, column=3)
        #Format odczytywanych rejestrów
        self.regFormat = tkinter.IntVar()
        self.decMode = tkinter.Radiobutton(self.f1, \
                                text="DEC", variable=self.regFormat, \
                                value=1,bg=bgColor,\
                                font=self.fontLabelek, fg=self.kolorLabelek,\
                                activebackground=bgColor,activeforeground=self.kolorLabelek,\
                                selectcolor=bgColor)
        self.decMode.grid(row=6, column=0)
        self.binMode = tkinter.Radiobutton(self.f1, \
                                text="BIN", variable=self.regFormat, \
                                value=2,bg=bgColor,\
                                font=self.fontLabelek, fg=self.kolorLabelek,\
                                activebackground=bgColor,activeforeground=self.kolorLabelek,\
                                selectcolor=bgColor)
        self.binMode.grid(row=6, column=1)
        self.hexMode = tkinter.Radiobutton(self.f1, \
                                text="HEX", variable=self.regFormat, \
                                value=3,bg=bgColor,\
                                font=self.fontLabelek, fg=self.kolorLabelek,\
                                activebackground=bgColor,activeforeground=self.kolorLabelek,\
                                selectcolor=bgColor)
        self.hexMode.grid(row=6, column=2)
        self.decMode.select()
        #Statystyki
        self.txcounter = 0
        requests = tkinter.Label(self.f4, text="Transmitted requests:", bg=bgColor,font=self.fontLabelek, fg=self.kolorLabelek)
        requests.grid(row=0, column=0)
        self.txrx = tkinter.Label(self.f4, text="{0}".format(self.txcounter),bg=bgColor,font=self.fontLabelek, fg=self.kolorLabelek)
        self.txrx.grid(row=0, column=1)
        #log:
        self.podpisLoga= tkinter.Label(self.f5, text="Transmission log", bg=bgColor,font=self.fontLabelek, fg=self.kolorLabelek)
        self.podpisLoga.grid(row=0, column=0, columnspan=4, pady=5)
        myFont = Font(family="Console", size=8)
        self.console = txt.ScrolledText(self.f5, background="black", font=myFont, foreground="green", width=105,height = 6)
        self.console.grid(row=1, column=0, columnspan=4)
        #-----------------------------------------------------------------------
#Druga zakładka:
        #Numer portu COM
        tkinter.Label(self.ModbusRTUsetings, text="COM port:",bg=bgColor,font=self.fontLabelek, fg=self.kolorLabelek).grid(row=0, column=0)
        if ports == []:
            ports = ["None"]
        ManualComPorts=["Manual port selection:",'COM1','COM2','COM3','COM4','COM5','COM6','COM7','COM8',\
                        'COM9','COM10','COM11','COM12','COM13','COM14','COM15',\
                        'COM16','COM17','COM18','COM19','COM20','COM21','COM22',\
                        'COM23','COM24','COM25','COM26','COM27','COM28','COM29',\
                        'COM30','COM31','COM32','COM33','COM34','COM35','COM36',\
                        'COM37','COM38','COM39','COM40','COM41','COM42','COM43',\
                        'COM44','COM45','COM46','COM47','COM48','COM49','COM50',\
                        'COM51','COM52','COM53','COM54','COM55','COM56','COM57',\
                        'COM58','COM59','COM60','COM61','COM62','COM63','COM64',\
                        'COM65','COM66','COM67','COM68','COM69','COM70','COM71',\
                        'COM72','COM73','COM74','COM75','COM76','COM77','COM78',\
                        'COM79','COM80','COM81','COM82','COM83','COM84','COM85',\
                        'COM86','COM87','COM88','COM89','COM90','COM91','COM92',\
                        'COM93','COM94','COM95','COM96','COM97','COM98','COM99','COM100']
        ports = ports + ManualComPorts
        self.PortCOM = ttk.Combobox(self.ModbusRTUsetings,state="readonly", values = ports) # tworzenie kontrolki Combobox
        self.PortCOM.grid(row=0, column=1) # umieszczenie kontrolki na oknie głównym
        self.PortCOM.current(0) # ustawienie domyślnego indeksu zaznaczenia
        #Baudrate
        self.BaudrateValue = ('50','75','110','134','150','300','600','1200',\
                            '1800','2400','4800','7200','9600','19200','38400',\
                            '57600','115200','230400','460800','921600')
        tkinter.Label(self.ModbusRTUsetings, text="Baudrate:",bg=bgColor,font=self.fontLabelek, fg=self.kolorLabelek).grid(row=0, column=2,pady=5, padx=5)
        self.Baudrate = ttk.Combobox(self.ModbusRTUsetings,state="readonly", values = self.BaudrateValue )
        self.Baudrate.grid(row=0, column=3, pady=5,padx=5)
        self.Baudrate.current(12)
        #Data bits
        self.databits = ('8')
        tkinter.Label(self.ModbusRTUsetings, text="Data bits:",bg=bgColor,font=self.fontLabelek, fg=self.kolorLabelek).grid(row=1, column=0,pady=5,padx=5)
        self.Bits = ttk.Combobox(self.ModbusRTUsetings,state="readonly", values = self.databits )
        self.Bits.grid(row=1, column=1, pady=5,padx=5)
        self.Bits.current(0)
        #Stop bits
        self.stopbitsValue = ('1','2')
        tkinter.Label(self.ModbusRTUsetings, text="Stop bits:",bg=bgColor,font=self.fontLabelek, fg=self.kolorLabelek).grid(row=1, column=2,pady=5,padx=5)
        self.stopbits = ttk.Combobox(self.ModbusRTUsetings,state="readonly", values = self.stopbitsValue )
        self.stopbits.grid(row=1, column=3, pady=5,padx=5)
        self.stopbits.current(0)
        #Parity
        self.parityCorrectValue = ('N','E','O','M','S')
        self.parityValue = ('None','Even','Odd','Mark','Space')    #PARITY_NONE, PARITY_EVEN, PARITY_ODDPARITY_MARK, PARITY_SPACE. Default to 'N'
        self.parity = tkinter.Label(self.ModbusRTUsetings, text="Parity:",bg=bgColor,font=self.fontLabelek, fg=self.kolorLabelek).grid(row=2, column=0,pady=5,padx=5)
        self.parity = ttk.Combobox(self.ModbusRTUsetings,state="readonly", values = self.parityValue)
        self.parity.grid(row=2, column=1, pady=5,padx=5)
        self.parity.current(0)

        FORMAT = ('%(asctime)-15s %(message)s')
        redir = RedirectText(self.console)
        logging.basicConfig(format=FORMAT,stream=redir, level=logging.DEBUG)
        log = logging.getLogger()
        log.setLevel(logging.DEBUG)

        # Przekierowanie wyjścia
        sys.stdout = redir

    def about(self):
        message = """Hi my name is Piotr, thanks you for using this software.
In the meantime please visit my github:
https://github.com/goclos\

Below license:
MIT License
Copyright (c) 2019 Piotr Gocłowski
Permission is hereby granted, free of charge, to any person obtaining a copy\
of this software and associated documentation files (the "Software"), to deal\
in the Software without restriction, including without limitation the rights\
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\
copies of the Software, and to permit persons to whom the Software is\
furnished to do so, subject to the following conditions:\
The above copyright notice and this permission notice shall be included in all\
copies or substantial portions of the Software.\
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\
SOFTWARE."""
        messagebox.showinfo("Info", message)
    #Funkcja przełączająca Modbus TCP / RTU
    def ModbusChange(self):
        #print(self.ModbusMode.get())
        if self.ModbusMode.get() == 1:
            self.ModbusTCPsettings.grid(row=1,column=0,columnspan=4)
            self.ModbusRTUsetings.grid_forget()
        if self.ModbusMode.get() == 2:
            self.ModbusTCPsettings.grid_forget()
            self.ModbusRTUsetings.grid(row=1,column=0,columnspan=4)

    def stopSending(self):
        self.stop_event.set()   #Tu wyłączany jest wątek odpytywania
        self.disco['state'] = 'normal'
        self.start['state'] = 'normal'
        self.timer.cancel()

    def startSending(self):
        self.stop_event.clear() #zerowanie eventu
        self.disco['state'] = 'disabled'
        self.start['state'] = 'disabled'
        self.stop['state'] = 'normal'
        self.timer = threading.Timer(float(self.poolInterval.get())/1000, self.readWrite)
        self.timer.start()

    def readWrite(self):
        print("")
        SelectedFuncCode = self.FuncCode.get()
        regs= 0
        try:
            #Funkcje odczytujące
            if SelectedFuncCode == '01-Read coils':
                regs = self.client.read_coils(int(self.startadres.get()), int(self.regCount.get()), unit = int(self.serverID.get()))
                zmienne = []
                for i in range(0, int(self.regCount.get())):
                    zmienne.append(regs.bits[i])
                for index in range(0, len(zmienne)):
                    self.polaRejestow[index].delete(0, 'end') #Usuwanie poprzedniej wartości
                    self.polaRejestow[index].insert(0, int(zmienne[index])) #Dodawanie nowej wartości

            if SelectedFuncCode == '02-Read Discrete Inputs':
                regs = self.client.read_discrete_inputs(int(self.startadres.get()), int(self.regCount.get()), unit = int(self.serverID.get()))
                zmienne = []
                for i in range(0, int(self.regCount.get())):
                    zmienne.append(regs.bits[i])
                for index in range(0, len(zmienne)):
                    self.polaRejestow[index].delete(0, 'end') #Usuwanie poprzedniej wartości
                    self.polaRejestow[index].insert(0, int(zmienne[index])) #Dodawanie nowej wartości

            if SelectedFuncCode == '03-Read holding Registers':
                regs = self.client.read_holding_registers(int(self.startadres.get()), int(self.regCount.get()), unit = int(self.serverID.get()))
                zmienne = []
                for i in range(0, int(self.regCount.get())):
                    zmienne.append(regs.registers[i])
                zmienne = self.changeBase(zmienne)
                for index in range(0, len(zmienne)):
                    self.polaRejestow[index].delete(0, 'end') #Usuwanie poprzedniej wartości
                    self.polaRejestow[index].insert(0, str(zmienne[index])) #Dodawanie nowej wartości

            if SelectedFuncCode == '04-Read input Registers':
                regs = self.client.read_input_registers(int(self.startadres.get()), int(self.regCount.get()), unit = int(self.serverID.get()))
                zmienne = []
                for i in range(0, int(self.regCount.get())):
                    zmienne.append(regs.registers[i])
                zmienne = self.changeBase(zmienne)
                for index in range(0, len(zmienne)):
                    self.polaRejestow[index].delete(0, 'end') #Usuwanie poprzedniej wartości
                    self.polaRejestow[index].insert(0, zmienne[index]) #Dodawanie nowej wartości

            #Funkcje zapisujące
            if SelectedFuncCode == '05-Write output coil':
                rejestrDozapisana = 0
                if self.polaRejestow[0].get() == "":
                    rejestrDozapisana = False
                else:
                    if not self.polaRejestow[0].get().isnumeric() and self.regFormat.get() != 3:
                        messagebox.showinfo("Info", 'Typed value is not numeric!')
                        self.stopSending()
                        self.console.see("end") #Przewijanie okna konsoli
                        return
                    rejestrDozapisana = bool(int(self.polaRejestow[0].get()))
                result = self.client.write_coil(int(self.startadres.get()), rejestrDozapisana, unit = int(self.serverID.get()))
                if result.function_code < 0x80:
                    print("Success! Value set")
                    self.start['state'] = 'normal'
                    self.stopSending()
                    self.console.see("end") #Przewijanie okna konsoli
                    return
                else:
                    print("Write coil failed")
                    self.stopSending()
                    self.console.see("end") #Przewijanie okna konsoli
                    return
            if SelectedFuncCode == '06-Write holding register':
                if not self.polaRejestow[0].get().isnumeric() and self.regFormat.get() != 3:
                    messagebox.showinfo("Info", 'Typed value is not numeric!')
                    self.stopSending()
                    self.console.see("end") #Przewijanie okna konsoli
                    return
                register = self.convertBaseToInt(self.polaRejestow[0].get())
                result = self.client.write_register(int(self.startadres.get()), register , unit = int(self.serverID.get()))
                if result.function_code < 0x80:
                    print("Success! Value set")
                    self.start['state'] = 'normal'
                    self.stopSending()
                    self.console.see("end") #Przewijanie okna konsoli
                    return
                else:
                    print("Write register failed")
                    self.stopSending()
                    self.console.see("end") #Przewijanie okna konsoli
                    return
            if SelectedFuncCode == '15-Write output coils' or SelectedFuncCode =='16-Write output registers':
                rejestryBool=[]
                rejestryInt=[]
                for i in range(0, int(self.regCount.get())):
                    if self.polaRejestow[i].get() == "":
                        rejestryBool.append(False)
                        rejestryInt.append(0)
                        continue
                    if not self.polaRejestow[i].get().isnumeric() and self.regFormat.get() != 3:
                        messagebox.showinfo("Info", 'Typed value is not numeric!')
                        self.stopSending()
                        self.console.see("end") #Przewijanie okna konsoli
                        return
                    if self.regFormat.get() != 3 and self.regFormat != 2:
                        rejestryBool.append(bool(int(self.polaRejestow[i].get())))
                    if self.regFormat.get() != 3 and self.regFormat != 2:
                        rejestryInt.append(int(self.polaRejestow[i].get()))
                    else:
                        rejestryInt.append(self.polaRejestow[i].get())

            if SelectedFuncCode == '15-Write output coils':
                result = self.client.write_coils(int(self.startadres.get()), rejestryBool, unit = int(self.serverID.get()))
                if result.function_code < 0x80:
                    print("Success! Coils set")
                    self.start['state'] = 'normal'
                    self.stopSending()
                    self.console.see("end") #Przewijanie okna konsoli
                    return
                else:
                    print("Write coils failed!")
                    self.stopSending()
                    self.console.see("end") #Przewijanie okna konsoli
                    return

            if SelectedFuncCode == '16-Write output registers':
                rejestryInt = self.convertBaseToInt(rejestryInt)
                result = self.client.write_registers(int(self.startadres.get()), rejestryInt, unit = int(self.serverID.get()))
                if result.function_code < 0x80:
                    print("Success! Coils set")
                    self.start['state'] = 'normal'
                    self.stopSending()
                    self.console.see("end") #Przewijanie okna konsoli
                    return
                else:
                    print("Write coils failed!")
                    self.stopSending()
                    self.console.see("end") #Przewijanie okna konsoli
                    return
        except Exception:
            traceback.print_exc()
            messagebox.showinfo("Info", "Exception, check communication logs!")
            self.stopSending()
            self.tcpClose()

        if regs == None:
            error_code = self.client.last_error()
            messagebox.showinfo("Info", 'Cannot connect or error code. Error Code={0}. {1}'.format(error_code, self.error_definition[int(error_code)]))
            self.txcounter = 0
            #print("Kod błędu: ",self.client.last_error())
            self.disconnected()
            return False

        self.txcounter += 1
        self.txrx['text'] = self.txcounter
        self.console.see("end") #Przewijanie okna konsoli
        if self.stop_event.is_set():    #Przerywanie wątku
            return
        self.timer = threading.Timer(float(self.poolInterval.get())/1000 , self.readWrite)
        self.timer.start()

    def changeBase(self,rejestry):
        if self.regFormat.get() == 1:
            return rejestry
        if self.regFormat.get() == 2:
            new_list = [bin(elem) for elem in rejestry]
            new_list = [str(elem[2:]) for elem in new_list]
        if self.regFormat.get() == 3:
            new_list = [hex(elem) for elem in rejestry]
            new_list = [str(elem[2:]) for elem in new_list]
        return new_list

    def convertBaseToInt(self, rejestr):
        if type(rejestr) == list:
            if self.regFormat.get() == 1:
                return rejestr
            if self.regFormat.get() == 2:
                rejestr = [int(str(elem),2) for elem in rejestr]
                return rejestr
            if self.regFormat.get() == 3:
                rejestr = [int(str(elem), 16) for elem in rejestr]
                return rejestr
        else:
            if self.regFormat.get() == 1:
                return int(rejestr)
            if self.regFormat.get() == 2:
                return int(rejestr, 2)
            if self.regFormat.get() == 3:
                return int(rejestr, 16)

    def on_select_changed(self,event):
        if str(self.FuncCode.get()) == '05-Write output coil' or str(self.FuncCode.get()) =='06-Write holding register':
            self.regCount.delete(0, 'end')
            self.regCount.insert(0, "1")
            self.regCount['state'] = 'disabled'
            for index in range(1, len(self.polaRejestow)):
                try:
                    self.polaRejestow[index].destroy()
                    self.labelkiRejestrow[index].destroy()
                except:
                    return

    def registerEntry(self, count, startLabel):
        #count = int(self.regCount.get())
        #startLabel = int(self.startadres.get())
        index = 0
        self.removeRegisterForms()
        while count != 0:              #Budowanie tabeli rejestrów
            for x in range(0,16,2):    #iterowanie po x
                for y in range(0,20):   #iterowanie po y
                    self.labelkiRejestrow [index] = tkinter.Label(self.f3 , text="{0}.".format(index+startLabel),bg=bgColor, font=self.fontLabelek, fg=self.kolorLabelek)
                    self.labelkiRejestrow [index].grid(row=4+y, column=x, sticky='e',padx=4,pady=1)
                    self.polaRejestow [index]= tkinter.Entry(self.f3,width=8, bd=1)
                    self.polaRejestow[index].insert(0, "0")
                    self.polaRejestow [index].grid(row=4+y, column=x+1,sticky='w',padx=4,pady=1)
                    index = index +1
                    count = count -1
                    if count == 0:
                        return True

    def removeRegisterForms(self):
        for index , element in enumerate(self.polaRejestow):
            self.polaRejestow[index].destroy()
            self.labelkiRejestrow[index].destroy()

    def tcpConnect(self):
        self.stop['state'] = 'disable'
        #Walidacja pól
        if not self.IPaddressValidate():
            return
        if not self.TCPportValidate():
            return
        if not self.ServerIDValidate():
            return
        if not self.StartAddressIDValidate():
            return
        if not self.RegCountValidate():
            return
        if not self.PoolIntervalValidate():
            return

        parityValue = None
        for i in range(0 , 5):
            if self.parityValue[i] == self.parity.get():
                parityValue = self.parityCorrectValue[i]
                #print(parityValue)
                break
        #print("slef.ModbusMode: ", self.ModbusMode.get())
        if self.ModbusMode.get() == 1: #TCP
            self.client = ModbusClient(host=self.IPaddress.get(), port=int(self.TCPport.get()),timeout=3)
            if not self.client.connect():  #Walidacja połączenia
                messagebox.showinfo("Info", 'Cannot connect to TCP slave / server, check IP address or/and TCP port')
                return

        else:                           #RTU
            self.client = ModbusSerialClient(method='rtu', port=str(self.PortCOM.get()),\
                                        stopbits=int(self.stopbits.get()), bytesize=8, \
                                        timeout=3, baudrate= int(self.Baudrate.get()), \
                                        parity = parityValue)
            if not self.client.connect():   #Walidacja otarcia portu COM
                messagebox.showinfo("Info", 'Cannot open such serial port, check if this port exist in system, and is not opened by another application')
                return

        self.connected()
        self.registerEntry(int(self.regCount.get()), int(self.startadres.get()))

    def tcpClose(self):
        self.client.close()
        self.removeRegisterForms()
        self.disconnected()
        self.txcounter = 0
        self.txrx['text'] = self.txcounter

    def disconnected(self):
        self.connect['state'] = 'normal'
        self.start['state'] = 'disabled'
        self.stop['state'] = 'disabled'
        self.disco['state'] = 'disabled'
        self.IPaddress['state'] = 'normal'
        self.TCPport['state'] = 'normal'
        self.serverID['state'] = 'normal'
        self.FuncCode['state'] = 'readonly'
        self.startadres['state'] = 'normal'
        self.regCount['state'] = 'normal'
        self.poolInterval['state'] = 'normal'
        self.ModbusRTUradio['state'] = 'normal'
        self.ModbusTCPradio['state'] = 'normal'


    def connected(self):
        self.connect['state'] = 'disabled'
        self.start['state'] = 'normal'
        self.stop['state'] = 'disabled'
        self.disco['state'] = 'normal'
        self.IPaddress['state'] = 'disabled'
        self.TCPport['state'] = 'disabled'
        self.serverID['state'] = 'disabled'
        self.FuncCode['state'] = 'disabled'
        self.startadres['state'] = 'disabled'
        self.regCount['state'] = 'disabled'
        self.poolInterval['state'] = 'disabled'
        self.ModbusRTUradio['state'] = 'disabled'
        self.ModbusTCPradio['state'] = 'disabled'


    def IPaddressValidate(self):
        return True

    def TCPportValidate(self):
        if self.TCPport.get().isdigit():
            if int(self.TCPport.get()) < 1 or int(self.TCPport.get()) > 65536:
                messagebox.showinfo("Info", 'TCP port out of range 1 - 65536')
                return False
            return True
        else:
            messagebox.showinfo("Info", 'TCP port is not digit!')
            return False

    def ServerIDValidate(self):
        if self.serverID.get().isdigit():
            if int(self.serverID.get()) < 1 or int(self.serverID.get()) > 255:
                messagebox.showinfo("Info", 'Slave ID out of range 1 - 255')
                return False
            return True
        else:
            messagebox.showinfo("Info", 'Server ID is not digit!')
            return False

    def StartAddressIDValidate(self):
        if self.startadres.get().isdigit():
            if int(self.startadres.get()) < 0 or int(self.startadres.get()) > 65536:
                messagebox.showinfo("Info", 'Start address out of range 0 - 65536!')
                return False
            return True
        else:
            messagebox.showinfo("Info", 'Start address is not digit')
            return False

    def RegCountValidate(self):
        if self.regCount.get().isdigit():
            if int(self.regCount.get()) == 0:
                messagebox.showinfo("Info", 'Register count cannot equal 0')
                return False
            elif int(self.regCount.get()) > 125:
                messagebox.showinfo("Info", 'Register count cannot exceed 125')
                return False
            return True
        else:
            messagebox.showinfo("Info", 'Register count is not digit')
            return False

    def PoolIntervalValidate(self):
        if self.poolInterval.get().isdigit():
            if int(self.poolInterval.get()) < 10 or int(self.poolInterval.get()) > 10000:
                messagebox.showinfo("Info", 'Pool interval out of range 10 - 10000 ms')
                return False
            return True
        else:
            messagebox.showinfo("Info", 'Pool interval is not digit!')
            return False

    def WordRegisterFormsValidate(self):
        for index in range(0, len(self.polaRejestow)):
            tempReg = int(self.polaRejestow[index].get())
            if tempReg < 0 or tempReg > 65536:
                messagebox.showinfo("Info", 'Register Value is out of range 0-65536')
                return False
            else:
                return True

    def BoolRegisterFormsValidate(self):
        for index in range(0, len(self.polaRejestow)):
            tempReg = int(self.polaRejestow[index].get())
            if tempReg != 0 or tempReg != 1 or self.polaRejestow[index].get() !='':
                messagebox.showinfo("Info", 'Coild register value is out of range 0 / 1')
                return False
            else:
                return True

def listSerialPorts():
    ports = [port[0] for port in serial.tools.list_ports.comports() if port[2] != 'n/a']
    #print(ports)    #jeśli puste to = []
    return ports

def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

if __name__ == "__main__":
    #bgColor = "#c4c4c4"
    bgColor = "#393e46"
    kolorLabelek = "#FFFFFF"
    ports = listSerialPorts()

    window = tkinter.Tk()
    windowWidth = window.winfo_reqwidth()
    windowHeight = window.winfo_reqheight()
    positionRight = int(window.winfo_screenwidth()/2 - windowWidth/2) -200
    positionDown = int(window.winfo_screenheight()/2 - windowHeight/2) - 400
    window.geometry("+{}+{}".format(positionRight, positionDown))
    window.minsize(700, 900)#minimalny rozmiar okna
    window.configure(background=bgColor)
    image_path = resource_path("ikona.ico")
    window.iconbitmap(default=image_path)
    GUI = GUI(window ,ports,bgColor,kolorLabelek)
    window.winfo_toplevel().title("Modbus Master TCP/RTU")
    window.mainloop()
