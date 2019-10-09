import tkinter
from tkinter import ttk
from tkinter import messagebox
from pyModbusTCP.client import ModbusClient
import time
import threading

class GUI:
    def __init__(self, window):
        odstepyX = 15
        odstepyY = 10
        self.kodyFunkcji = ('01-Read coils','02-Read Discrete Inputs','03-Read holding Registers',\
                            '04-Read input Registers','05-Write output coil','06-Write holding register',\
                            '15-Write output coils','16-Write output registers')
        self.polaRejestow = {}
        self.labelkiRejestrow = {}
        self.client = 0
        #window.resizable(False, False)
        tabcontrol = ttk.Notebook(window) #Komponent który kontroluje B
        self.f1 = ttk.Frame(tabcontrol)   # Pierwsza strona
        self.f2 = ttk.Frame(tabcontrol)   # Druga strona
        self.f3 = ttk.Frame(self.f1)      # Ramka z rejestrami w zakładce pierwszej
        self.f3.grid(row=5, column=0, sticky='w',columnspan=4, padx=20, pady=20)
        tabcontrol.pack(expan=1,fill="both")
        tabcontrol.pack(expan=1,fill="both")
        tabcontrol.add(self.f1, text='Master')
        tabcontrol.add(self.f2, text='Slave')
        #Adres IP
        tkinter.Label(self.f1, text="IP address:").grid(row=0, column=0)
        self.IPaddress = tkinter.Entry(self.f1)
        self.IPaddress.grid(row=0, column=1,padx = odstepyX, pady=odstepyY)
        self.IPaddress.insert(0, "192.168.0.1")
        #Port TCP
        tkinter.Label(self.f1, text="TCP port:").grid(row=0, column=2)
        self.TCPport = tkinter.Entry(self.f1)
        self.TCPport.grid(row=0, column=3,padx = odstepyX, pady=odstepyY)
        self.TCPport.insert(0, "502")
        #Server ID
        tkinter.Label(self.f1, text="Server / Slave ID:").grid(row=1, column=0)
        self.serverID = tkinter.Entry(self.f1)
        self.serverID.grid(row=1, column=1,padx = odstepyX , pady=odstepyY)
        self.serverID.insert(0, "1")
        #Function code
        tkinter.Label(self.f1, text="Function code:").grid(row=1, column=2)
        self.FuncCode = ttk.Combobox(self.f1, values = self.kodyFunkcji,state="readonly") # tworzenie kontrolki Combobox
        self.FuncCode.bind('<<ComboboxSelected>>', self.on_select_changed)
        self.FuncCode.grid(row=1, column=3) # umieszczenie kontrolki na oknie głównym
        self.FuncCode.current(0) # ustawienie domyślnego indeksu zaznaczenia
        #self.FuncCode.bind("<<ComboboxSelected>>") # podpięcie metody pod zdarzenie zmiany zaznaczenia
        #Start address
        tkinter.Label(self.f1, text="Start address(dec):").grid(row=2, column=0)
        self.startadres = tkinter.Entry(self.f1)
        self.startadres.grid(row=2, column=1,padx = odstepyX, pady=odstepyY )
        self.startadres.insert(0, "0")
        #register count
        tkinter.Label(self.f1, text="Register count:").grid(row=3, column=0)
        self.regCount = tkinter.Entry(self.f1)
        self.regCount.grid(row=3, column=1,padx = odstepyX, pady=odstepyY )
        self.regCount.insert(0, "1")
        #Pool interval
        tkinter.Label(self.f1, text="Poll interval(ms):").grid(row=2, column=2)
        self.poolInterval = tkinter.Entry(self.f1)
        self.poolInterval.grid(row=2, column=3,padx = odstepyX , pady=odstepyY)
        self.poolInterval.insert(0, "500")
        #Przyciski Start stop
        self.connect = tkinter.Button(self.f1, text = "Connect", height=2, width=10, command=self.tcpConnect)
        self.connect.grid(row=4, column=0)
        self.start = tkinter.Button(self.f1, text = "Start", height=2, width=10, command=self.readWrite, state='disabled')
        self.start.grid(row=4, column=1)
        self.stop = tkinter.Button(self.f1, text = "Stop", height=2,width=10, state='disabled')
        self.stop.grid(row=4, column=2)
        self.disco = tkinter.Button(self.f1, text = "Disconnect", height=2, width=10, command=self.tcpClose, state='disabled')
        self.disco.grid(row=4, column=3)

        #Druga zakładka:
        self.close_btn = tkinter.Button(self.f2, text = "Close", command = window.quit) # closing the 'window' when you click the button
        self.close_btn.grid(row=4, column=0)

    def readWriteThreat():
        pass

    def readWrite(self):
        #self.kodyFunkcji[i]
        ModbusMethods = [self.client.read_coils, self.client.read_discrete_inputs, \
                        self.client.read_holding_registers, self.client.read_input_registers,\
                        self.client.write_single_coil,  self.client.write_single_register, \
                        self.client.write_multiple_coils,  self.client.write_multiple_registers]
        SelectedFuncCode = self.FuncCode.get()
        regs= 0
        #Funkcje odczytujące
        if SelectedFuncCode == '01-Read coils':
            regs = self.client.read_coils(int(self.startadres.get()), int(self.regCount.get()))
        if SelectedFuncCode == '02-Read Discrete Inputs':
            regs = self.client.read_discrete_inputs(int(self.startadres.get()))
        if SelectedFuncCode == '03-Read holding Registers':
            regs = self.client.read_holding_registers(int(self.startadres.get()), int(self.regCount.get()))
        if SelectedFuncCode == '04-Read input Registers':
            regs = self.client.read_input_registers(int(self.startadres.get()), int(self.regCount.get()))
        #Funkcje zapisujące
        if SelectedFuncCode == '05-Write output coil':
            #Walidacja rejestrów
            result = self.client.write_single_coil(int(self.startadres.get()), bool(int(self.polaRejestow[0].get())))
            if result:
                print("Success! Value set")
                return
            else:
                print("Write coil failed")
                return
        if SelectedFuncCode == '06-Write holding register':
            result = self.client.write_single_register(int(self.startadres.get()), int(self.polaRejestow[0].get()))
            if result:
                print("Success! Value set")
                return
            else:
                print("Write register failed")
                return
        if SelectedFuncCode == '15-Write output coils' or SelectedFuncCode =='16-Write output registers':
            rejestryBool=[]
            rejestryInt=[]
            for i in range(0, len(self.polaRejestow)):
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
                return
            else:
                print("Write coils failed!")
                return
        if SelectedFuncCode == '16-Write output registers':
            result = self.client.write_multiple_registers(int(self.startadres.get()), rejestryInt)
            if result:
                print("Success! Coils set")
                return
            else:
                print("Write coils failed!")
                return
        #regs = self.client.read_holding_registers(int(self.startadres.get()), int(self.regCount.get()))
        print(self.FuncCode.get())
        if regs== None:
            messagebox.showinfo("Info", 'Cannot connect to slave/server')
            self.disconnected()
            return False
        print("!!!---!!!---!!!",type(regs), regs)
        for index , element in enumerate(regs):
            print(index, element)
            self.polaRejestow[index].delete(0, 'end') #Usuwanie poprzedniej wartości
            self.polaRejestow[index].insert(0, element) #Dodawanie nowej wartości
        print(regs)

    def say_hi(self):
        tkinter.Label(self.f2, text = self.IPaddress.get()).grid(row=5, column=0)

    def on_select_changed(self,event):
        print(event)
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

    def registerEntry(self):
        count = int(self.regCount.get())
        index = 0
        startLabel = count
        while count != 0:              #Budowanie form rejestrów
            for x in range(0,16,2):    #iterowanie po x
                for y in range(0,30):   #iterowanie po y
                    self.labelkiRejestrow [index] = tkinter.Label(self.f3 , text="{0}.".format(index+startLabel))
                    self.labelkiRejestrow [index].grid(row=4+y, column=x, sticky='e')
                    self.polaRejestow [index]= tkinter.Entry(self.f3 )
                    self.polaRejestow[index].insert(0, "0")
                    self.polaRejestow [index].grid(row=4+y, column=x+1,sticky='w')
                    index = index +1
                    count = count -1
                    if count == 0:
                        return True
                        
    def RemoveRegisterForms(self):
        for index , element in enumerate(self.polaRejestow):
            self.polaRejestow[index].destroy()
            self.labelkiRejestrow[index].destroy()

    def tcpConnect(self):
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
        print(self.IPaddress.get(),  self.TCPport.get())
        try:
            self.client = ModbusClient(host=str(self.IPaddress.get()), \
            port=int(self.TCPport.get()), auto_open=True,timeout=3, unit_id=int(self.serverID.get()))
        except ValueError:
            print("Error with host or port params", ValueError)
            return
        self.connected()
        print(self.client)
        self.registerEntry()

    def tcpClose(self):
        self.client.close()
        self.disconnected()
        self.RemoveRegisterForms()


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
        self.stop['state'] = 'normal'
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


if __name__ == "__main__":
    window = tkinter.Tk()
    windowWidth = window.winfo_reqwidth()
    windowHeight = window.winfo_reqheight()
    positionRight = int(window.winfo_screenwidth()/2 - windowWidth/2)
    positionDown = int(window.winfo_screenheight()/2 - windowHeight/2)
    window.geometry("+{}+{}".format(positionRight, positionDown))
    #window.geometry("800x800")
    window.title("Modbus TCP simulator")
    GUI = GUI(window)

    window.mainloop()
