import tkinter
from tkinter import ttk
from tkinter import messagebox
import tkinter.scrolledtext as txt
from tkinter.font import Font
from pyModbusTCP.client import ModbusClient
import time
import threading
import logging
from pymodbus.payload import BinaryPayloadDecoder
import sys
import glob
import serial.tools.list_ports


class RedirectText(object):
    def __init__(self, text_ctrl):
        self.output = text_ctrl

    def write(self, string):
        self.output.insert(tkinter.END, string)

class GUI:
    def __init__(self, window, ports):
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
        self.stop_event = threading.Event() #Definiowanie zdarzenia aby móc zatrzymać wątek wysyłania zapytań
        self.Fmain = ttk.Frame(window)
        self.Fmain.pack()
        #tabcontrol = ttk.Notebook(self.Fmain) #Komponent który kontroluje B
        self.ModbusRadioButtons = ttk.Frame(self.Fmain)
        self.f1 = ttk.Frame(self.Fmain)   # Ustawienia ogolne Modbus
        self.ModbusTCPsettings = ttk.Frame(self.Fmain)
        self.ModbusRTUsetings = ttk.Frame(self.Fmain)   # Ustawienia Modbus RTU
        self.f3 = ttk.Frame(self.Fmain)      # Ramka z rejestrami w zakładce pierwszej
        self.f4 = ttk.Frame(self.Fmain)       #statystyki
        self.f5 = ttk.Frame(self.Fmain)         #konsola tx/rx
        #Pakowanie
        self.ModbusRadioButtons.grid(row=0,column=0,columnspan=4,pady=10)
        self.ModbusTCPsettings.grid(row=1,column=0,columnspan=4)
        #self.ModbusRTUsetings.grid(row=1,column=0,columnspan=4,pady=20)
        self.f1.grid(row=2,column=0,columnspan=4,pady=20)
        self.f3.grid(row=3,column=0,columnspan=4)    #Ramka z rejestrami
        self.f4.grid(row=4,column=0,columnspan=4)    #Ramka ze statystykami
        self.f5.grid(row=5,column=0,columnspan=4)   #Ramka z logiem



        self.ModbusMode = tkinter.IntVar()
        self.ModbusTCPradio = tkinter.Radiobutton(self.ModbusRadioButtons, text="Modbus TCP", variable=self.ModbusMode, value=1, command = self.ModbusChange)
        self.ModbusTCPradio.grid(row=0, column=0)
        self.ModbusRTUradio = tkinter.Radiobutton(self.ModbusRadioButtons, text="Modbus RTU", variable=self.ModbusMode, value=2, command = self.ModbusChange)
        self.ModbusRTUradio.grid(row=0, column=1)
        self.ModbusTCPradio.select()

        #Adres IP
        tkinter.Label(self.ModbusTCPsettings, text="IP address:").grid(row=1, column=0)
        self.IPaddress = tkinter.Entry(self.ModbusTCPsettings, width=15)
        self.IPaddress.grid(row=1, column=1,padx = odstepyX, pady=odstepyY)
        self.IPaddress.insert(0, "127.0.0.1")
        #Port TCP
        tkinter.Label(self.ModbusTCPsettings, text="TCP port:").grid(row=1, column=2)
        self.TCPport = tkinter.Entry(self.ModbusTCPsettings)
        self.TCPport.grid(row=1, column=3,padx = odstepyX, pady=odstepyY)
        self.TCPport.insert(0, "502")
        #Server ID
        tkinter.Label(self.f1, text="Server / Slave ID:").grid(row=2, column=0)
        self.serverID = tkinter.Entry(self.f1,width=15)
        self.serverID.grid(row=2, column=1,padx = odstepyX , pady=odstepyY)
        self.serverID.insert(0, "1")
        #Function code
        tkinter.Label(self.f1, text="Function code:").grid(row=2, column=2)
        self.FuncCode = ttk.Combobox(self.f1, values = self.kodyFunkcji,state="readonly") # tworzenie kontrolki Combobox
        self.FuncCode.bind('<<ComboboxSelected>>', self.on_select_changed)
        self.FuncCode.grid(row=2, column=3) # umieszczenie kontrolki na oknie głównym
        self.FuncCode.current(0) # ustawienie domyślnego indeksu zaznaczenia
        #Start address
        tkinter.Label(self.f1, text="Start address (dec):").grid(row=3, column=0)
        self.startadres = tkinter.Entry(self.f1,width=15)
        self.startadres.grid(row=3, column=1,padx = odstepyX, pady=odstepyY )
        self.startadres.insert(0, "0")
        #register count
        tkinter.Label(self.f1, text="Register count:").grid(row=4, column=0)
        self.regCount = tkinter.Entry(self.f1,width=15)
        self.regCount.grid(row=4, column=1,padx = odstepyX, pady=odstepyY )
        self.regCount.insert(0, "1")
        #Pool interval
        tkinter.Label(self.f1, text="Poll interval (ms):").grid(row=3, column=2)
        self.poolInterval = tkinter.Entry(self.f1)
        self.poolInterval.grid(row=3, column=3,padx = odstepyX , pady=odstepyY)
        self.poolInterval.insert(0, "500")
        #Przyciski Start stop
        self.connect = tkinter.Button(self.f1, text = "Connect", height=2, width=10, command=self.tcpConnect)
        self.connect.grid(row=5, column=0)
        self.start = tkinter.Button(self.f1, text = "Start", height=2, width=10, command=self.startSending, state='disabled')
        self.start.grid(row=5, column=1)
        self.stop = tkinter.Button(self.f1, text = "Stop", height=2,width=10, command=self.stopSending, state='disabled')
        self.stop.grid(row=5, column=2)
        self.disco = tkinter.Button(self.f1, text = "Disconnect", height=2, width=10, command=self.tcpClose, state='disabled')
        self.disco.grid(row=5, column=3)
        #Statystyki
        self.txcounter = 0
        tkinter.Label(self.f4, text="Transmitted requests:").grid(row=0, column=0)
        self.txrx = tkinter.Label(self.f4, text="{0}".format(self.txcounter))
        self.txrx.grid(row=0, column=1)
        #log:
        myFont = Font(family="Console", size=8)
        self.console = txt.ScrolledText(self.f5, background="black", font=myFont, foreground="green", width=105,height = 10)
        self.console.grid(row=1, column=0, columnspan=4, pady=20)

        #-----------------------------------------------------------------------
#Druga zakładka:
        #Numer portu COM
        tkinter.Label(self.ModbusRTUsetings, text="COM port:").grid(row=0, column=0)
        if ports == []:
            ports = ["None"]
        self.PortCOM = ttk.Combobox(self.ModbusRTUsetings,state="readonly", values = ports) # tworzenie kontrolki Combobox
        self.PortCOM.grid(row=0, column=1) # umieszczenie kontrolki na oknie głównym
        self.PortCOM.current(0) # ustawienie domyślnego indeksu zaznaczenia



        # redirect stdout
        redir = RedirectText(self.console)
        sys.stdout = redir
        # Wylistowanie labelek i form rejestrow
        self.registerEntry(125, 0)

    def ModbusChange(self):
        print(self.ModbusMode.get())
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
        print("\n#",self.txcounter,": ")
        SelectedFuncCode = self.FuncCode.get()
        regs= 0
        #Funkcje odczytujące
        if SelectedFuncCode == '01-Read coils':
            regs = self.client.read_coils(int(self.startadres.get()), int(self.regCount.get()))
        if SelectedFuncCode == '02-Read Discrete Inputs':
            regs = self.client.read_discrete_inputs(int(self.startadres.get()),int(self.regCount.get()))
        if SelectedFuncCode == '03-Read holding Registers':
            regs = self.client.read_holding_registers(int(self.startadres.get()), int(self.regCount.get()))
        if SelectedFuncCode == '04-Read input Registers':
            regs = self.client.read_input_registers(int(self.startadres.get()), int(self.regCount.get()))
        #Funkcje zapisujące
        if SelectedFuncCode == '05-Write output coil':
            rejestrDozapisana = 0
            if self.polaRejestow[0].get() == "":
                rejestrDozapisana = False
            else:
                rejestrDozapisana = bool(int(self.polaRejestow[0].get()))
            result = self.client.write_single_coil(int(self.startadres.get()), rejestrDozapisana)
            if result:
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
            result = self.client.write_single_register(int(self.startadres.get()), int(self.polaRejestow[0].get()))
            if result:
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
                rejestryBool.append(bool(int(self.polaRejestow[i].get())))
                rejestryInt.append(int(self.polaRejestow[i].get()))
        if SelectedFuncCode == '15-Write output coils':
            result = self.client.write_multiple_coils(int(self.startadres.get()), rejestryBool)
            if result:
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
            result = self.client.write_multiple_registers(int(self.startadres.get()), rejestryInt)
            if result:
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
        if regs == None:
            error_code = self.client.last_error()
            messagebox.showinfo("Info", 'Cannot connect or error code. Error Code={0}. {1}'.format(error_code, self.error_definition[int(error_code)]))
            self.txcounter = 0
            #print("Kod błędu: ",self.client.last_error())
            self.disconnected()
            return False
        for index , element in enumerate(regs):
            #print(index, element)
            self.polaRejestow[index].delete(0, 'end') #Usuwanie poprzedniej wartości
            self.polaRejestow[index].insert(0, element) #Dodawanie nowej wartości
        self.txcounter += 1
        self.txrx['text'] = self.txcounter
        self.console.see("end") #Przewijanie okna konsoli
        if self.stop_event.is_set():
            return
        self.timer = threading.Timer(float(self.poolInterval.get())/1000 , self.readWrite)
        self.timer.start()

    def on_select_changed(self,event):
        #print(event)
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
        #messagebox.showinfo("Info", self.cb_value.get())

    def registerEntry(self, count, startLabel):
        #count = int(self.regCount.get())
        #startLabel = int(self.startadres.get())
        index = 0
        self.removeRegisterForms()
        while count != 0:              #Budowanie form rejestrów
            for x in range(0,16,2):    #iterowanie po x
                for y in range(0,20):   #iterowanie po y
                    self.labelkiRejestrow [index] = tkinter.Label(self.f3 , text="{0}.".format(index+startLabel))
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
        #print(self.IPaddress.get(),  self.TCPport.get())
        try:
            self.client = ModbusClient(host=str(self.IPaddress.get()), \
            port=int(self.TCPport.get()), auto_open=True,timeout=3, unit_id=int(self.serverID.get()),debug=True)
        except ValueError:
            print("Error with host or port params", ValueError)
            return
        self.connected()
        #print(self.client)
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
    print(ports)    #jeśli puste to = []
    return ports

if __name__ == "__main__":
    ports = listSerialPorts()

    window = tkinter.Tk()
    windowWidth = window.winfo_reqwidth()
    windowHeight = window.winfo_reqheight()
    positionRight = int(window.winfo_screenwidth()/2 - windowWidth/2) -200
    positionDown = int(window.winfo_screenheight()/2 - windowHeight/2) - 400
    window.geometry("+{}+{}".format(positionRight, positionDown))
    window.minsize(700, 900)#minimalny rozmiar okna
    GUI = GUI(window ,ports)
    window.winfo_toplevel().title("Modbus Tester")
    window.mainloop()
