
# This is the control interface for the EMG EMS Auto-Calibration

# This allows you to select to simply explore the EMS array manually
# or calibrate a gesture using EMG and then explore it using EMS.

# If calibrating a gesture, you will be prompted to perform one 'rest'
# gesture first, before performing your gesture of choice. 

# <Escape> will exit the program

# import graphics packages for display
import Tkinter as tkinter
import tkFont

# import other files
import Sleeve_Link
import Read_EMG
import File_Link
from Process_EMG import *

# import time and graphing utilities
import time
import matplotlib
matplotlib.use("TkAgg")
from matplotlib import pyplot as plt

#Electrode Sleeve Details
num_electrode_rows = 10
num_electrode_cols = 6
start_electrode_row = 0
upper_row = 0
bottom_row = 9
upper_set = True
lower_set = True

# Draw command control buttons to screen
def draw_commands():
	lbl_commands.pack()
	btn_author.pack()
	lbl_calibrate.pack()

# Display pose instructions for calibration process
def display_instruction_tkinter(pose, root):
	instruct = tkinter.Toplevel(root)
	instruct.geometry('800x500+700+300')
	customFont = tkFont.Font(family="Helvetica", size=40)
	if pose == 2:
		label_instruct = tkinter.Label(instruct, text="Actively hold a pose")
	elif pose == 1:
		label_instruct = tkinter.Label(instruct, text="Just relax...")
	else:
		label_instruct = tkinter.Label(instruct, text="And relax")
	label_instruct.pack(anchor='center', expand=True)

	instruct.bind("<KeyPress>", lambda e: close_instruction_tkinter(instruct))
	instruct.mainloop()

# Close pose instruction window
def close_instruction_tkinter(root):
	root.destroy()
	root.quit()

# Run EMG-EMS calibration process
def run_EMG_EMS(btn_stim, window):
	print "Running Auto-Calibration"

	global gesture_no, num_electrode_rows, num_electrode_cols, start_electrode_row, participant_no, panel
	global upper_row, bottom_row

	#Start with rest gesture to get base data
	display_instruction_tkinter(1, window)

	print "running EMG ", participant_no, gesture_no, "resting"
	Read_EMG.run_EMG_Read_process(participant_no, 0, num_electrode_rows, num_electrode_cols, start_electrode_row, upper_row, bottom_row, 0)

	#Display image telling participant to relax
	display_instruction_tkinter(0, window)

	#Display target gesture and give time to examine
	display_instruction_tkinter(2, window)

	#Run EMG reading
	print "running EMG ", participant_no, gesture_no, curr_gesture
	Read_EMG.run_EMG_Read_process(participant_no, 1, num_electrode_rows, num_electrode_cols, start_electrode_row, upper_row, bottom_row, 1)

	#Display image telling participant to relax
	display_instruction_tkinter(0, window)

	# Crunch EMG data and display on EMS controller for exploration
	stim_points, stim_proportions, stim_proportions_norm_ = read_and_crunch_data(0, 1, upper_row, bottom_row, 1)
	setup_stim_process(0, 1, window, stim_points[0], stim_proportions[0], stim_proportions_norm_[0], num_electrode_rows, num_electrode_cols)

# Run basic EMS authoring process
def run_EMS_Authoring(participant_ID, gesture_ID, root, sequence=False):
	if not sequence:
		run_pose_tkinter(participant_ID, gesture_ID, root, [], [], [], num_electrode_rows, num_electrode_cols, True, True, False)
	else:
		run_pose_tkinter(participant_no, gesture_ID, root, [], [], [], num_electrode_rows, num_electrode_cols, True, True, True)

def cancel_all(root):
	cv2.destroyAllWindows()
	_quit(root, False)

#Create control window
window = tkinter.Tk()
window.geometry('600x600')
uppermidFrame = tkinter.Frame(window)
uppermidFrame.pack()
lowermidFrame = tkinter.Frame(window)
lowermidFrame.pack()
frame = tkinter.Frame(window)
frame.pack()
midFrame = tkinter.Frame(window)
midFrame.pack()
bottomFrame = tkinter.Frame(window)
bottomFrame.pack(side = "bottom")

#Create study command buttons
lbl_commands = tkinter.Label(frame, text=" Study Controls")
lbl_testing = tkinter.Label(frame, text=" Testing Controls")
btn_author = tkinter.Button(frame, text="Control GUI", command= lambda: run_EMS_Authoring(0, 0, window, True))
btn_calibrate = tkinter.Button(frame, text="Calibrate: EMG->EMS", command= lambda: runEMG_EMS(btn_stim, window))

# Populate study command buttons to screen
draw_commands()

# Bind escape button to exit
window.bind("<Escape>", lambda : cancel_all(window))

#Activate window control
window.mainloop()


