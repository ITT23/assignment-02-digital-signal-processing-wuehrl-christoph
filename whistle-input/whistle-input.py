# program controlled by frequency chirps
# it has a pyglet mode and a mod that controls the arrow up and arrow down key
# At first an audio device and the mode must be selected
# The program should by closed by the terminal
# only tested with singing not whistling
import pyaudio
import numpy as np
import pyglet
from pynput.keyboard import Key, Controller


WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600

CHUNK_SIZE = 3675  # Number of audio frames per buffer, low for latency reasons
FORMAT = pyaudio.paInt16  # Audio format
CHANNELS = 1  # Mono audio
RATE = 44100  # Audio sampling rate (Hz)
THRESHOLD_LOUDNESS = 1000000
THRESHOLD_SINGING = int(10000 / (RATE/CHUNK_SIZE)) # in Hz data above this threshold can be ignored because it is not singable or can be achieved by whistling
NUMBER_OF_RECTANGLES = 5
NUMBER_OF_FREQUENCY_CHANGE = 4 # How many times in a row the frequency must go up or down to be detected
KEYBOARD = Controller()
pyglet_selected = False # shows selected mode


p = pyaudio.PyAudio()
stream = None

last_note = 0 # safe position of the last note to detect if tone change is upwards or downwards
counter_up = 0 # counts how many times the dominant frequency goes up
counter_down = 0 # counts how many times the dominant frequency goes down
red_rectangle_position = 0 # keeps track of the red rectangle

def main():
    setup_device()
    choose_application()

# choose between pyglet application and arrow button control
def choose_application():
    print('select application')
    print('1 - pyglet test application')
    print('2 - control arrows application')

    application = int(input())
    if(application == 1):
        setup_pyglet()
    elif(application == 2):
        setup_pynput()

# choose input device and setup stream
def setup_device():
    global stream
    global red_rectangle_position
    # print info about audio devices
    # let user select audio device
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')

    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            print("Input Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))

    print('select audio device:')
    input_device = int(input())

    # open audio input stream
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK_SIZE,
                    input_device_index=input_device)
    
# sets up pyglet application
def setup_pyglet():
    global pyglet_selected
    pyglet_selected = True
    win = pyglet.window.Window(WINDOW_WIDTH, WINDOW_HEIGHT)
    rects = pyglet.graphics.Batch()
    rectangles =[]
    
    # sets up the rectangles
    for i in range(NUMBER_OF_RECTANGLES + 1):
        rectangles.append(pyglet.shapes.Rectangle(150, WINDOW_HEIGHT - 50 * i - 40, 20, 20, color=(255, 255, 255), batch=rects))
    rectangles[red_rectangle_position].color = (255, 0, 0)

    #draw cycle
    @win.event
    def on_draw():
        global red_rectangle_position
        win.clear()
        rects.draw()
        check_note()
        for rect in rectangles:
            rect.color = (255, 255, 255)
        rectangles[red_rectangle_position].color = (255, 0, 0)

    pyglet.app.run()

# sets up arrow control application
def setup_pynput():
    while(True):  
        check_note()

# checks the current main frequency
def check_note():
    data = stream.read(CHUNK_SIZE)

    # Convert audio data to numpy array
    data = np.frombuffer(data, dtype=np.int16)

    # calculate spectrum using a fast fourier transform
    spectrum = np.abs(np.fft.rfft(data))

    main_frequency = find_main_frequency(spectrum[0:THRESHOLD_SINGING])
    main_frequency = main_frequency[0][0]

    # only use data beyond a certain threshold
    if(spectrum[main_frequency] < THRESHOLD_LOUDNESS):
        return
    
    check_last_note(main_frequency)


    
    
# checks if dominant frequency goes up or down and how many times in a row
def check_last_note(main_frequency):
    global last_note, counter_up, counter_down
    if(main_frequency > last_note):
        counter_up += 1
        if (counter_up >= NUMBER_OF_FREQUENCY_CHANGE):
            counter_up = 0
            if(pyglet_selected):
                pyglet_up() # triggers pyglet input
            else:
                KEYBOARD.press(Key.up) # triggers arrow input
    elif(main_frequency == last_note):
        return 
    else:
        counter_up = 0

    if(main_frequency < last_note):
        counter_down += 1
        if (counter_down >= NUMBER_OF_FREQUENCY_CHANGE):
            counter_down = 0
            if(pyglet_selected):
                pyglet_down() # triggers pyglet input
            else:
                KEYBOARD.press(Key.down)  # triggers arrow input
    elif(main_frequency == last_note):
        return 
    else:
        counter_down = 0
    
    last_note = main_frequency

# returns the position of the main frequency
def find_main_frequency(data):
    highest_frequency = max(data)
    return np.where(data == highest_frequency)

# moves the red square up
def pyglet_up():
    global red_rectangle_position
    if(red_rectangle_position == 0):
        red_rectangle_position = NUMBER_OF_RECTANGLES
    else:
        red_rectangle_position -= 1

# moves the red square down
def pyglet_down():
    global red_rectangle_position
    if(red_rectangle_position == NUMBER_OF_RECTANGLES):
        red_rectangle_position = 0
    else:
        red_rectangle_position += 1
    
main()