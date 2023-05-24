import PySimpleGUI as sg

sg.theme('DarkAmber')   # Add a touch of color
# All the stuff inside your window.
layout = [  
            [sg.Text('Select a day to review events')],
            [sg.CalendarButton('Choose Date', target=(1,0), key='date')],
            [sg.Text('To review a specific event ')],
            [sg.Text('Enter the event ID'),  sg.InputText(size=25),],
            [sg.Text('To review an observation')],
            [sg.Text('Enter the station ID and file name'), sg.InputText(size=8), sg.InputText()],

            [sg.Button('Ok'), sg.Button('Cancel')] ]

# Create the Window
window = sg.Window('All Sky Network', layout)
# Event Loop to process "events" and get the "values" of the inputs
while True:
    event, values = window.read()
    print("VALS:", values)
    #sg.Popup(values['date'])
    if event == sg.WIN_CLOSED or event == 'Cancel': # if user closes window or clicks cancel
        break
    if "date" in values:
       print('You entered date', values['date'] )
       print('You entered ', values[0], values[1])
    else:
       print('You entered ', values[0], values[1])
window.close()
