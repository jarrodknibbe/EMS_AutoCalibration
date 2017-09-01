
#----------------------
#Electrode visualisation class
#Draws representations of sleeve array and controls
#Enables control of parameters
#----------------------

#Import libraries
import numpy as np
import cv2
import serial
import time
import datetime
import pytz
import random
import matplotlib
matplotlib.use("TkAgg")
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
import Tkinter as tkinter
from PIL import Image
from collections import deque
import os
import io
import subprocess
import threading
import math

# Import neighbor/support classes
from Gesture_Sequencer import *
from Sleeve_Link import send_command, set_controller_amplitude, set_controller_freq_pwm, set_sleeve_electrodes, set_all_sleeve_electrodes, reset_connection
from File_Link import initialise_file, write_single_line_file, write_sleeve_status_to_file, find_number_of_poses, write_electrodes_to_file, load_pose_list

#True if running from EMG data
calibrated_pose = False

#Track number of active electrodes, only turn on EMS if > 2
num_active_electrodes = 0

#Initialise stimulation parameters, electrode array representations, etc.
EMG_ch1 = 0
EMG_ch2 = 0
EMG_pwm = 0
EMG_freq = 0
data = np.zeros(shape=(0,0))

#Ramps up to a predefined amplitude, with 0.03s step
#Input - start amplitude, target/end amplitude
def ramp_to_amplitude(start_amp, end_amp):
	global EMG_ch2, EMG_ch1, stim_Ratio

	EMG_ch2 = 0
	EMG_ch1 = 0
	set_controller_amplitude()

	for i in range(start_amp,end_amp):
		EMG_ch2 += 1
		EMG_ch1 = int(EMG_ch2 * stim_Ratio)
		set_controller_amplitude()

		time.sleep(0.03)

	print "Ramp Done"

#Function called when sleeve array clicked
def control_stim_electrode(event):
	electrode_selected = [int(event.x/40), int(event.y/30)]
	global electrodes, data
	electrodes.itemconfig("rec" + str(electrode_selected[0]) + "_" + str(electrode_selected[1]), fill="blue")

	#If left mouse click, increase channel selection
	if event.num == 1:

		pre_value = 0
		data[electrode_selected[1]][electrode_selected[0]] += 1
		data[electrode_selected[1]][electrode_selected[0]] %= 5
		
	#If right mouse click, turn off electrode
	if event.num != 1:
		print "Right click - disengage"
		pre_value = data[electrode_selected[1]][electrode_selected[0]]
		data[electrode_selected[1]][electrode_selected[0]] = 0

	load_balancing(data[electrode_selected[1]][electrode_selected[0]], False, False, pre_value)
	global EMG_ch1, EMG_ch2
	set_controller_amplitude(EMG_ch1, EMG_ch2)
	set_sleeve_electrodes(electrode_selected[0], electrode_selected[1], data[electrode_selected[1]][electrode_selected[0]])

	update_sleeve_drawing()
	update_controls_drawing()

#triggered when stim control bars clicked
def control_stim_signal(event):
	click_location = 4
	click_value = event.x
	if event.x > 0 and event.x < 250:
		click_location = int(event.y/60)

		#0 = pwm, 1 = freq, 2 = ch1, 3 = ch2
		if click_location == 0:
			global EMG_pwm
			EMG_pwm = int(click_value)
			set_controller_freq_pwm(EMG_pwm, EMG_freq)
		elif click_location == 1:
			global EMG_freq
			EMG_freq = int(click_value)
			set_controller_freq_pwm(EMG_pwm, EMG_freq)
		elif click_location == 2:
			global EMG_ch1, EMG_ch2, stim_Ratio, calibrated_pose
			EMG_ch1 = int(click_value)
			load_balancing(0, True, False)
			set_controller_amplitude(EMG_ch1, EMG_ch2)
		elif click_location == 3:
			global EMG_ch2, EMG_ch1, stim_Ratio, calibrated_pose
			EMG_ch2 = int(click_value)
			load_balancing(0, True, True)
			set_controller_amplitude(EMG_ch1, EMG_ch2)

		time.sleep(0.1)
		send_sock_command(participant_ID_, 1, curr_gesture)
		global participant_ID_, pose_number
		write_sleeve_status_to_file(participant_ID_, pose_number, True, "machine", electrodes, data, curr_gesture, EMG_ch1, EMG_ch2, EMG_pwm, EMG_freq)

	update_controls_drawing()

#handle keyboard shortcuts for signal control
def keyboard_control_stim(event):
	print "Keypress ", event.char
	chan2_change = False

	global EMG_ch1, EMG_ch2, stim_Ratio, calibrated_pose, EMG_freq, EMG_pwm, stop_EMS_ramp, playLoop, curr_gesture
	if event.char == 'm':
		EMG_ch2 += 1
		chan2_change = True
	elif event.char == 'n':
		EMG_ch2 -= 1
		chan2_change = True
		if EMG_ch2 <= 0:
			EMG_ch2 = 0
	elif event.char == 'c':
		EMG_ch1 -= 1
		if EMG_ch1 <= 0:
			EMG_ch1 = 0
	elif event.char == 'v':
		EMG_ch1 += 1
	elif event.char == ' ':
		EMG_ch2 = 0
		EMG_ch1 = 0
		stop_EMS_ramp = True
		playLoop = False
	elif event.char == 'g':
		EMG_freq += 1
	elif event.char == 'f':
		EMG_freq -= 1
	elif event.char == 'h':
		EMG_pwm -= 1
	elif event.char == 'j':
		EMG_pwm += 1
	else:
		global data, key_poses
		for targets in key_poses:
			if event.char == targets[0]:
				data = np.copy(targets[1])
				EMG_ch1 = targets[2]
				EMG_ch2 = targets[3]
				EMG_freq = targets[4]
				EMG_pwm = targets[5]

				#Update drawings based on input
				update_sleeve_drawing()
				set_all_sleeve_electrodes()
				update_sleeve_drawing()

	#Ensure safe load balance
	#If multiple electrodes are removed, make sure amplitude is decreased
	load_balancing(0, True, chan2_change)

	#Trigger optitrack if either channel % 5 equals 0
	#Random(ish) step, change to increase/decrease 
	if EMG_ch2%5 == 0 or EMG_ch1%5 == 0:
		send_sock_command(participant_ID_, 1, curr_gesture)
	
	#set amplitudes and frequences, update graphics
	set_controller_amplitude(EMG_ch1, EMG_ch2)
	set_controller_freq_pwm(EMG_pwm, EMG_freq)
	update_controls_drawing()

#Re-draw sleeve graphic
def update_sleeve_drawing():
	global electrodes, num_electrode_rows, num_electrode_cols
	color_fill = ["white", "blue", "green", "red", "purple"]
	for x in range(0, num_electrode_cols):
		for y in range(0, num_electrode_rows):
				electrodes.itemconfig("rec" + str(x) + "_" + str(y), fill=color_fill[int(data[y][x])])

#redraw controls graphic
def update_controls_drawing():
	global controls, EMG_ch1, EMG_ch2, EMG_freq, EMG_pwm
	controls.coords("line0", (EMG_pwm, 0, EMG_pwm, 60))
	controls.coords("line1", (EMG_freq, 60, EMG_freq, 120))
	controls.coords("line2", (EMG_ch1, 120, EMG_ch1, 180))
	controls.coords("line3", (EMG_ch2, 180, EMG_ch2, 240))

#Balance loads, to maintain channel 1 and channel 2 ratios
def load_balancing(channel_change, amp_increase=False, ch2_increase=False, pre_channel=0):
	global stim_Ratio, EMG_ch2, EMG_ch1, calibrated_pose
	num_per_ch2 = len(zip(*np.where(data == 3)))
	num_per_ch1 = len(zip(*np.where(data == 1)))

	if not amp_increase:
		EMG_ch2 -= 20
		if EMG_ch2 <= 0:
			EMG_ch2 = 10

	if calibrated_pose and num_per_ch2 > 0:
		stim_per_e2 = (EMG_ch2 / (num_per_ch2))
		EMG_ch1 = int(stim_per_e2 * stim_Ratio) * num_per_ch1
	elif not calibrated_pose and not amp_increase:
		EMG_ch1 -= 20
		if EMG_ch1 <= 0:
			EMG_ch1 = 10

#Check that layouts are valid
#Valid layouts allow a child below a parent, or one to the left and right
#overflowing at the edges to wrap around
def check_valid_layout():
	global data, EMG_ch1, EMG_ch2

	if len(zip(*np.where(data == 3))) == 0 or len(zip(*np.where(data == 4))) == 0:
		print data
		data[np.abs(data) == 3] = 0
		data[np.abs(data) == 4] = 0
		EMG_ch2 = 0
		# print data
	if len(zip(*np.where(data == 1))) == 0 or len(zip(*np.where(data == 2))) == 0:
		print data
		data[np.abs(data) == 2] = 0
		data[np.abs(data) == 1] = 0
		EMG_ch1 = 0
		# print data

	#Loop through whole data array
	for i in range(0,10):
		for j in range(0,6):

			#If electrode is a child
			if data[i][j] == 4 or data[i][j] == 2:

				#check eligible electrodes for parent
				parent = False
				check_rows = [j-1, j, j+1]
				if check_rows[0] == -1:
					check_rows[0] = 5
				elif check_rows[2] == 6:
					check_rows[2] = 0

				for p_i in range(max(i-2, 0), i):
					for p_j in check_rows:
						if data[p_i][p_j] == data[i][j]-1:
							parent = True

				if not parent:
					data[i][j] = 0

	ch2_top = zip(*np.where(data==3))
	ch2_bot = zip(*np.where(data==4))

def continue_button_controls(participant_ID, gesture_no, flag, owner):
	global electrodes, data, curr_gesture, EMG_ch1, EMG_ch2, EMG_pwm, EMG_freq
	write_sleeve_status_to_file(participant_ID, gesture_no, flag, owner, electrodes, data, curr_gesture, EMG_ch1, EMG_ch2, EMG_pwm, EMG_freq)
	if owner == "machine":
		global calibrated_pose
		calibrated_pose = False
	elif owner == "human":
		_quit(stim_window, flag)

#Main function that loads graphics
#can take in calibrated data
#Input:
#ParticipantID - unique id for saving data
#Gesture no - unique number for gesture saving
#new_win - primary tkinter window for controlling update loop
#stim_points, stim_proportions, stim_proportions_norm - electrode selection, and relative channel amplidtudes
#num_electrode_rows_, num_electrodes_cols_ - size of sleeve
#raw - False by default, True = no calibration data provided
#authoring = False by default, True = display mapping gesture to key window
#sequencer = False by default, True = display sequencer window
def run_pose_tkinter(participant_ID, gesture_no, new_win, stim_points, stim_proportions, stim_proportions_norm, num_electrode_rows_, num_electrode_cols_, raw=False, authoring=False, sequencer=False):
	global stim_window
	stim_window = tkinter.Toplevel(new_win)
	stim_window.title("EMS Controls")
	stim_window.geometry('+600+500')
	stim_window.lift()

	set_color_map()

	global electrodes, controls
	left_frame = tkinter.Frame(stim_window)
	left_frame.pack(side="left")
	top_label = tkinter.Label(left_frame, text="TOP SLEEVE")
	top_label.pack()
	electrodes = tkinter.Canvas(left_frame, width = 240, height=300)
	electrodes.bind('<Button>', control_stim_electrode)

	#Create Sleeve
	for i in range(0,6):
		for j in range(0,10):
			electrodes.create_rectangle(40*i, 30*j, 40*(i+1), 30*(j+1), tags="rec" + str(i) + "_" + str(j))
	electrodes.pack()

	#Create signal controllers
	right_frame = tkinter.Frame(stim_window)
	right_frame.pack(side="left", padx=(20,10))
	controls_label = tkinter.Label(right_frame, text="SIGNAL CONTROLS")
	controls_label.pack()
	controls = tkinter.Canvas(right_frame, width=280, height=300)
	controls.bind('<Button>', control_stim_signal)

	controls_text = ["PWM", "FREQ", "AMP1", "AMP2"]
	start_y = 50
	for i in range(0,4):
		controls.create_text(30, (60*i)+20, font="Helvetica", text=controls_text[i])
		controls.create_rectangle(1,(60*i), 250, 60*(i+1), tags="sig" + str(i))
		controls.create_line(41, (60*i), 41, 60*(i+1), tags="line" + str(i))
	controls.pack(padx=(20,10))

	bottom_label = tkinter.Label(left_frame, text="BOTTOM SLEEVE")
	bottom_label.pack()

	global calibrated_pose
	calibrated_pose = not raw

	#Make electrode sleeve size global
	global num_electrode_rows, num_electrode_cols, curr_gesture, participant_ID_
	num_electrode_rows = num_electrode_rows_
	num_electrode_cols = num_electrode_cols_
	curr_gesture = gesture_no
	participant_ID_ = participant_ID

	#Tell Arduino we are doing EMS
	global EMS_active
	command = "5c"
	send_command(True, command)
	EMS_active = True

	#set freq/pwm data from...
	global EMG_pwm, EMG_freq
	EMG_pwm = 200
	EMG_freq = 170
	set_controller_freq_pwm(EMG_pwm, EMG_freq)

	global EMG_ch1, EMG_ch2
	EMG_ch1 = 5
	EMG_ch2 = 5
	set_controller_amplitude(EMG_ch1, EMG_ch2)
	

	#Initialise ELectrode Data Store
	global data
	data = np.zeros(shape=(num_electrode_rows,num_electrode_cols))

	#Map stim values to channel selections
	stim_vals_chans = [0, 0, 1, 2, 3, 4]

	if not raw:
		#set amplitude data from stim_proportions
		global stim_Ratio
		stim_Ratio = stim_proportions[1]
		max_stim = 15

		#Loop through stimulation arrays and set coordinates
		for stim_coords_groups, stim_vals in zip(stim_points, stim_proportions_norm):
			if stim_vals > 0:
				for stim_coords in stim_coords_groups:
					data[int(stim_coords[0])][int(stim_coords[1])] = stim_vals_chans[stim_vals * 2]
					data[int(stim_coords[2])][int(stim_coords[3])] = stim_vals_chans[(stim_vals * 2) + 1]

		check_valid_layout()

		#Send sleeve commands for data parameters
		for locs in np.argwhere(data > 0.):
			set_sleeve_electrodes(locs[1], locs[0], data[locs[0]][locs[1]])
	else:
		EMG_ch1 = 1
		EMG_ch2 = 1

	set_controller_freq_pwm(EMG_pwm, EMG_freq)
	set_controller_amplitude(EMG_ch1, EMG_ch2)

	update_sleeve_drawing()
	update_controls_drawing()

	bottom_frame = tkinter.Frame(stim_window)
	bottom_frame.pack()

	stim_window.bind("<KeyPress>", keyboard_control_stim)

	if not authoring and not sequencer:
		global save_machine_button, save_button
		bottom_frame = tkinter.Frame(stim_window)
		bottom_frame.pack()
		save_machine_button = tkinter.Button(master=bottom_frame, text="Continue", command= lambda: continue_button_controls(participant_ID, gesture_no, True, "machine"))
		save_machine_button.pack()
		save_button = tkinter.Button(master=bottom_frame, text="Done", command= lambda: continue_button_controls(participant_ID, gesture_no, True, "human"))
		save_button.pack()
		button = tkinter.Button(master=bottom_frame, text='Quit', command= lambda: _quit(stim_window, raw))
		button.pack()

		reset_connection_button = tkinter.Button(master=bottom_frame, text="Reset", command= lambda: reset_connection())
		reset_connection_button.pack(pady=(10,0))
	elif authoring:

		initialise_file(participant_ID, gesture_no, True)

		author_tools_window = tkinter.Toplevel(stim_window)
		author_tools_window.title("Gesture Author")
		author_tools_window.geometry('+1230+520')
		move_patterns = tkinter.Frame(author_tools_window)
		move_patterns.pack()
		map_keys_frame = tkinter.Frame(author_tools_window)
		map_keys_frame.pack()
		save_load_frame = tkinter.Frame(author_tools_window)
		save_load_frame.pack()


		global pose_no, key_poses
		move_pattern_labels = ["left", "up", "down", "right"]
		move_pattern_buttons = []
		for move_ in move_pattern_labels:
			move_pattern_buttons.append(tkinter.Button(master=move_patterns, text=move_, command= lambda motion=move_: translate_electrodes(motion)))
			move_pattern_buttons[-1].pack(side="left", pady=(10, 10))
		map_pose_label = tkinter.Label(master=map_keys_frame, text="Map pose to Number key:")
		map_pose_label.pack()
		global map_pose_key_entry
		map_pose_key_entry = tkinter.Entry(master=map_keys_frame)
		map_pose_key_entry.pack()
		map_pose_key = tkinter.Button(master=map_keys_frame, text="Map", command = lambda : bind_pose_to_key(author_tools_window))
		map_pose_key.pack(pady=(5, 10))
		
		author_tools_window.bind("<KeyPress>", keyboard_control_stim)

	if sequencer:

		#Create sequencer variables
		global ch1_sequence, ch2_sequence
		for i in range(0,20):
			ch1_sequence.append(sequence_event(np.zeros(data.shape), 0))
			ch2_sequence.append(sequence_event(np.zeros(data.shape), 0))
			emg_sequence.append(0)
		
		#Create new window for sequencer
		timeline_window = tkinter.Toplevel(stim_window)
		timeline_window.title("Gesture Sequencer")
		timeline_window.geometry('+1500+510')
		timeline_frame = tkinter.Frame(timeline_window)
		timeline_frame.pack()

		timeline_window.bind("<KeyPress>", keyboard_control_stim)

		#Add timeline
		global timeStart, timeEnd, timelineCanvas
		timelineCanvas = tkinter.Canvas(timeline_frame, width=300, height=200)
		timelineCanvas.create_rectangle(20, 70, 280, 120, tags="timeline")
		timelineCanvas.create_line(20,60,21,160, tags="time", fill="red")

		#Add locations for item placement
		start_loc_x = 20
		for i in range(0,20):
			timelineCanvas.create_rectangle(20 + (i * 13), 70, 20 + (i+1) * 13, 90, tags="ch1_" + str(i))
			timelineCanvas.create_rectangle(20 + (i * 13), 100, 20 + (i+1) * 13, 120, tags="ch2_" + str(i))
			timelineCanvas.create_rectangle(20 + (i * 13), 130, 20 + (i+1) * 13, 150, tags="emg_" + str(i))
		timelineCanvas.pack()

		#Add control buttons
		global EMG_labels
		EMG_labels = tkinter.Label(timeline_frame, text="EMG: 'wrist up', 'wrist down")
		EMG_labels.pack()
		timeEnd = tkinter.Entry(timeline_frame)
		timeEnd.pack()
		startTimeBar = tkinter.Button(timeline_frame, text="Play", command= lambda: timeBarButtonpress(stim_window))
		startTimeBar.pack()
		global playLoop, pauseLoop
		stopTimeBar = tkinter.Button(timeline_frame, text="Stop", command= lambda: stop_sequence_play(timeline_window))
		stopTimeBar.pack()

		#Bind mouse controls
		timelineCanvas.bind("<Button-1>", lambda e: sequencer_controls(e, "down"))
		timelineCanvas.bind("<B1-Motion>", lambda e: sequencer_controls(e, "drag"))
		timelineCanvas.bind("<ButtonRelease-1>", lambda e: sequencer_controls(e, "up"))
		timelineCanvas.bind("<Button-2>", lambda e: sequencer_controls(e, "right"))

	stim_window.protocol("WM_DELETE_WINDOW", lambda : _quit(stim_window, raw))
	stim_window.mainloop()

#Flip off EMS and re-enable
def reset_connection():
	command = "3c"
	send_command(True, command)

	time.sleep(1)
	command = "5c"
	send_command(True, command)
	EMS_active = True

	global data
	set_all_sleeve_electrodes(data)
	set_controller_amplitude(EMG_ch1, EMG_ch2)
	set_controller_freq_pwm(EMG_pwm, EMG_freq)

#move all electrodes up, down, left or right
#input - "up", "down", "left", "right"
def translate_electrodes(translation_):
	global data, EMG_ch2, EMG_ch1
	print "translate electrodes"
	elec_ = np.zeros(data.shape)
	print "data.shape", data.shape
	print "translation = ", translation_
	for rows in range(0,data.shape[0]):
		for cols in range(0,data.shape[1]):
			if translation_ == "up":
				if rows > 0:
					elec_[rows-1][cols] = data[rows][cols]
				else:
					elec_[data.shape[0]-1][cols] = data[rows][cols]
			elif translation_ == "down":
				if rows < (data.shape[0]-1):
					elec_[rows+1][cols] = data[rows][cols]
				else:
					elec_[(rows+1)%(data.shape[0])][cols] = data[rows][cols]
			elif translation_ == "left":
				if cols > 0:
					elec_[rows][cols-1] = data[rows][cols]
				else:
					elec_[rows][data.shape[1]-1] = data[rows][cols]
			elif translation_ == "right":
				if cols < (data.shape[1]-1):
					elec_[rows][cols+1] = data[rows][cols]
				else:
					elec_[rows][(cols+1)%(data.shape[1])] = data[rows][cols]
	data = np.copy(elec_)
	update_sleeve_drawing()
	set_all_sleeve_electrodes()
	EMG_ch1 = 0
	EMG_ch2 = 0
	set_controller_amplitude()

# Specify an amplitude to run EMS calibration up to over a short time
def run_EMS_to_amp(frequency, pulse_width, amp, channel):
	global EMG_pwm, EMG_freq, EMG_ch2, stop_EMS_ramp
	stop_EMS_ramp = False
	EMG_pwm = pulse_width
	EMG_freq = frequency
	set_controller_freq_pwm()

	if channel == 2:
		EMG_ch2 = 0
		set_controller_amplitude()

		for i in range(EMG_ch2,int(amp)):
			EMG_ch2 += 1
			set_controller_amplitude()
			
			time.sleep(1.2 / float(amp))

			if stop_EMS_ramp:
				EMG_ch2 = 0
				set_controller_amplitude()

			# update_controls_drawing()
	elif channel == 1:
		EMG_ch1 = 0
		set_controller_amplitude()

		for i in range(EMG_ch1,int(amp)):
			EMG_ch1 += 1
			set_controller_amplitude()
			
			time.sleep(1.2 / float(amp))

			if stop_EMS_ramp:
				EMG_ch1 = 0
				set_controller_amplitude()

			# update_controls_drawing()

#initialise color map to show channel selection
def set_color_map():
	global cmap, norm
	cmap = matplotlib.colors.ListedColormap(['white', 'blue', 'green', 'red', 'purple'])
	bounds=[0,1,2,3,4,5]
	norm = matplotlib.colors.BoundaryNorm(bounds, cmap.N)

# Quit controls for EMS
def _quit(root, raw):
	# if raw:
	# 	write_sleeve_status_to_file()
	# 	close_file()
	global EMG_ch1, EMG_ch2
	EMG_ch1 = 0
	EMG_ch2 = 0
	set_controller_amplitude(EMG_ch1, EMG_ch2)
	command = "3c"
	send_command(True, command)
	global stim_window
	stim_window.destroy()
	stim_window.quit()

# This file can be run as a standalone, by simply running this file.
if __name__ == "__main__":
	window = tkinter.Tk()
	run_pose_tkinter(5,1,window,0, 0, 0,10,6,True, True, True)