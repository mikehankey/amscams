import PySimpleGUI as sg

sg.theme('DarkAmber')   # Add a touch of color
# All the stuff inside your window.
layout = [  [sg.Text('Event Reviews')],
            [sg.Text('Enter the date (YYYY_MM_DD) for review'), sg.InputText()],
            [sg.Button('Ok'), sg.Button('Quit')] ]

# Create the Window
window = sg.Window('ALLSKY7 NETWORK ADMIN', layout)
# Event Loop to process "events" and get the "values" of the inputs
while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == 'Cancel': # if user closes window or clicks cancel
        break
    print('You entered ', values[0])

window.close()
