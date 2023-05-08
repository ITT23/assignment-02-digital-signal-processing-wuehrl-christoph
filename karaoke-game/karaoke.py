# Program to train your pitch with a little game
# Select your audio device in the terminal
# There will be random notes between c3 and c4 you can get points by hitting the correct note
# Close the program in the terminal
import pyglet
import pyaudio
import numpy as np
import random

# Constants for pyglet
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
PLAYER_SIZE = WINDOW_HEIGHT / 8
NOTE_SIZE = PLAYER_SIZE * 4
NOTE_SPEED = 10
PLAYER_WIDTH = 10
RATE_TO_GENERATE_NOTES = 50
NOTES_BATCH = pyglet.graphics.Batch()
CORRECT_NOTES_BATCH = pyglet.graphics.Batch()
NOTE_LINES_BATCH = pyglet.graphics.Batch()


CHUNK_SIZE = 6300  # Number of audio frames per buffer for a ok resolution and latency
FORMAT = pyaudio.paInt16  # Audio format
CHANNELS = 1  # Mono audio
RATE = 44100  # Audio sampling rate (Hz)
DATA_THRESHOLD = 700000
OVERTONE_THRESHOLD = 1000000
NOT_SINGABLE_THRESHOLD =  int(5000 / (RATE/CHUNK_SIZE)) # in Hz data above this threshold can be ignored because it is not singable

p = pyaudio.PyAudio()
stream = None

ticks = 0 #count ticks of the draw cycle for time
note_list = [] 
points = 0
correct_notes = []

# keys for the game relative to the resolution
NOTE_FREQUENCY = {
    'c3' : int(138 / (RATE/CHUNK_SIZE)),
    'd3' : int(146 / (RATE/CHUNK_SIZE)),
    'e3' : int(164 / (RATE/CHUNK_SIZE)),
    'f3' : int(174 / (RATE/CHUNK_SIZE)),
    'g3' : int(196 / (RATE/CHUNK_SIZE)),
    'a3' : int(220 / (RATE/CHUNK_SIZE)),
    'b3' : int(246 / (RATE/CHUNK_SIZE)),
    'c4' : int(261 / (RATE/CHUNK_SIZE)),
}

# player positions for the keys relative to the window height
NOTE_POSITION = {
    'c3' : WINDOW_HEIGHT - PLAYER_SIZE * 8,
    'd3' : WINDOW_HEIGHT - PLAYER_SIZE * 7,
    'e3' : WINDOW_HEIGHT - PLAYER_SIZE * 6,
    'f3' : WINDOW_HEIGHT - PLAYER_SIZE * 5,
    'g3' : WINDOW_HEIGHT - PLAYER_SIZE * 4,
    'a3' : WINDOW_HEIGHT - PLAYER_SIZE * 3,
    'b3' : WINDOW_HEIGHT - PLAYER_SIZE * 2,
    'c4' : WINDOW_HEIGHT - PLAYER_SIZE,
}


def main():
    setup_device()
    win = pyglet.window.Window(WINDOW_WIDTH, WINDOW_HEIGHT)
    
    player = pyglet.shapes.Rectangle(WINDOW_WIDTH / 2 - PLAYER_WIDTH/ 2, WINDOW_HEIGHT / 2 - PLAYER_SIZE / 2, PLAYER_WIDTH, PLAYER_SIZE, color=(255, 255, 255))
    note_lines = []
    
    for i in range(8):
        note_lines.append(pyglet.shapes.Line(0, PLAYER_SIZE * i + PLAYER_SIZE, WINDOW_WIDTH, PLAYER_SIZE * i + PLAYER_SIZE, 3, color=(255,255,255), batch=NOTE_LINES_BATCH))

    #draw cycle
    @win.event
    def on_draw():
        global points
        
        create_new_note()
        move_notes()

        #sets player position
        position = get_new_position()
        if(position != None):
            player.y = position

        # checks if player and note are in the same position
        if(check_collision(player, note_list)):
            points += 5
            correct_notes.append(pyglet.shapes.Rectangle(player.x, player.y, player.width, player.height, color=(0, 130, 0), batch=CORRECT_NOTES_BATCH))

        #draws all elements
        win.clear()
        NOTES_BATCH.draw()
        CORRECT_NOTES_BATCH.draw()
        player.draw()
        points_label = pyglet.text.Label(f"Points: {points}", font_name='Times New Roman', font_size=12, x=WINDOW_WIDTH - WINDOW_WIDTH/10, y=WINDOW_HEIGHT - WINDOW_HEIGHT/10)
        points_label.draw()
        NOTE_LINES_BATCH.draw()

    pyglet.app.run()

# Opens input stream for audio device
def setup_device():
    global stream
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

# returns the player position for a sung key 
def get_new_position():
    key = get_note()
    if(key == None):
        return WINDOW_HEIGHT # if there is no key sung or it is below c3 or above c4 move the player out of the window 
    return NOTE_POSITION[key]

# gets audio, analyze for the main frequency and returns the corresponding key form the key dict
def get_note():
    data = stream.read(CHUNK_SIZE)

    # Convert audio data to numpy array
    data = np.frombuffer(data, dtype=np.int16)

    # calculate spectrum using a fast fourier transform
    spectrum = np.abs(np.fft.fft(data))

    #finds the main frequency
    main_frequency = find_main_frequency(spectrum[0:NOT_SINGABLE_THRESHOLD])
    main_frequency = main_frequency[0][0]

    # don't analyze the data if it is below a certain threshold
    if(spectrum[main_frequency] < DATA_THRESHOLD):
        return
        
    # analyzes for to dominant overtones
    main_frequency = overtone_correction(spectrum, main_frequency)
    
    # checks if the dominant frequency is in the frequency dict
    current_note = check_frequency(main_frequency)
    return current_note

# searches the output of the fft for the most dominant frequency
def find_main_frequency(data):
    highest_frequency = max(data)
    return np.where(data == highest_frequency)

# checks if main frequency (with a little tolerance) is in the note dict
def check_frequency(frequency):
    keys = list(NOTE_FREQUENCY)
    for key in keys:
        if(frequency > NOTE_FREQUENCY[key] - 2 and frequency < NOTE_FREQUENCY[key] + 2):
            return key
    
# analyses for to dominant overtones
def overtone_correction(spectrum, frequency):
    if(spectrum[int(frequency/3)] > OVERTONE_THRESHOLD):
        return int(frequency/3)
    if(spectrum[int(frequency/2)] > OVERTONE_THRESHOLD):
        return int(frequency/2)
    return frequency

# creates a note with random length and position
def create_note(rect_batch):
    keys = list(NOTE_POSITION)
    random_note = random.randint(0, len(keys) - 1)
    random_length = random.randint(4,8) /10
    return pyglet.shapes.Rectangle(WINDOW_WIDTH, NOTE_POSITION[keys[random_note]], NOTE_SIZE * random_length, PLAYER_SIZE, color=(0, 0, 255), batch=rect_batch)

# checks if note and player are in the same position
def check_collision(player, rectangles):
    for rect in rectangles:
        if(rect.x <= WINDOW_WIDTH/2 and rect.x + rect.width >= WINDOW_WIDTH/2):
            if(player.y == rect.y):
                return True
    return False

# creates new note after a set number of ticks
def create_new_note():
    global note_list, ticks
    if(ticks % RATE_TO_GENERATE_NOTES == 0):
        note_list.append(create_note(NOTES_BATCH))
        ticks = 0
    ticks += 1

# moves notes to a set speed
def move_notes():
    global note_list, correct_notes
    for rect in note_list:
        rect.x -= NOTE_SPEED
    for rect in correct_notes:
        rect.x -= NOTE_SPEED

main()