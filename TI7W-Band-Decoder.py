
from tkinter import *

from tkinter import ttk

import json,socket,xmltodict

global is_on
global radio_freq
global init
init=False
radio_freq=0
is_on=True

def get_Ant(frq):
    if frq < 2000:
        return (1) #160
    elif frq < 4000:
        return (2) #80
    elif frq < 6000:
        return (12) #60
    elif frq < 8000:
        return (3) #40
    elif frq < 11000:
        return (4) #30
    elif frq < 15000:
        return (5) # 20
    elif frq < 19000:
        return (6) #17
    elif frq < 22000:
        return (7) #15
    elif frq < 25000:
        return (8) #12
    elif frq < 30000:
        return (9) #10
    elif frq < 60000:
        return (11) #6

def set_AG(ipaddr,tcp_port,radio_nr,ant_port):
    tcp_str=("!000a!00cc80!" + (str(radio_nr)) + ";" + (str((ant_port))))
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ipaddr, tcp_port))
            #s.sendall(tcp_str)
            s.sendall((bytes(tcp_str, 'utf-8')))
    except Exception as e: print(e)

def freq_update():
    global is_on
    global radio_freq
    if is_on == False:
        try:
            UDP_IP = ipaddr.get()
            UDP_PORT = eval(udpport.get())
            sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            sock.settimeout(5)# UDP
            sock.bind((UDP_IP, UDP_PORT))
            data, addr = sock.recvfrom(2048)
            xml_str=(data.decode("utf-8"))
            radio_dict=(json.loads((json.dumps(xmltodict.parse(xml_str)))))
            if radio_dict["RadioInfo"]["RadioNr"]=="1":
                freq=(eval(radio_dict["RadioInfo"]["Freq"])/100)
                radio_freq=freq
                radfreq.config(text=((str(freq))+ " kHz"))
                set_AG(AG_IP.get(),eval(AG_TCP.get()),AG_RF.get(),get_Ant(radio_freq))
        except:
            print ("UDP Data Timeout")

        
    window.after(500, freq_update)

def switch():
    global is_on
    global init
    if is_on:
        on_button.config(fg = "red",text="Stop")
        is_on = False
    else:
        on_button.config(fg = "green",text="Start")
        init = False
        is_on = True







window = Tk()

window.title("FreqControl")

tab_control = ttk.Notebook(window)


tab1 = ttk.Frame(tab_control)
tab2 = ttk.Frame(tab_control)
tab3 = ttk.Frame(tab_control)




Label(tab1, text="Logger IP Address:").grid(row=0)
ipaddr=Entry(tab1)
ipaddr.grid(column=1, row=0)
ipaddr.insert(0,"127.0.0.1")

Label(tab1, text="Logger UDP Port:").grid(row=1)
udpport=Entry(tab1)
udpport.grid(column=1, row=1)
udpport.insert(0,"12060")

Label(tab1, text="Radio Freq:").grid(row=4)
radfreq=Label(tab1,text="FreqHere")
radfreq.grid(column=1, row=4)

on_button = Button(tab1,text="Start", bd = 0, command=switch, fg="green",)
on_button.grid(row=3,column=1)


Label(tab2, text="IP Address:").grid(row=0)
AG_IP=Entry(tab2)
AG_IP.grid(column=1, row=0)
AG_IP.insert(0,"192.168.1.140")

Label(tab2, text="TCP Port:").grid(row=1)
AG_TCP=Entry(tab2)
AG_TCP.grid(column=1, row=1)
AG_TCP.insert(0,"9007")

Label(tab2, text="AG Port:").grid(row=2)
AG_RF=Entry(tab2)
AG_RF.grid(column=1, row=2)
AG_RF.insert(0,"1")



tab_control.add(tab1, text='Freq Data')
tab_control.add(tab3, text='BPF Control')
tab_control.add(tab2, text='4O3A Band Ports')

##lbl1 = Label(tab1, text= 'label1')
##
##lbl1.grid(column=0, row=0)
##
##lbl2 = Label(tab2, text= 'label2')
##
##lbl2.grid(column=0, row=0)
##
tab_control.pack(expand=1, fill='both')
window.after(100,freq_update)
window.mainloop()
