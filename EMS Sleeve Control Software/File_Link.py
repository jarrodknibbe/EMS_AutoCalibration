
# 'Class' for controlling file reading, writing, creating, etc.

# import dependancies (some might be redundant)
import os
import io
from collections import deque
import scipy.signal as sg
import numpy as np
import Tkinter as tkinter
from PIL import Image
import datetime
import pytz

#Add data instances to a deque, then write to file and pop
file_write_queue = deque()
stop_file_writing_flag = False

#Store current participantID and output file name
participant_ID = 0
output_file = ""

pose_number = 0

# Write Electrode data to a file
def write_electrodes_to_file(participant_ID, data):
	global pose_number
	filename = "data/participant_" + str(participant_ID) + "/Raw_P" + str(pose_number) + ".npy"
	np.save(filename, data)
	pose_number += 1

# Load electrode data from a file to array image
def load_electrodes_from_file(participant_ID, pose_no):
	filename = "data/participant_" + str(participant_ID) + "/Raw_P" + str(pose_no) + ".npy"
	electrodes_ = np.load(filename)
	print "Loaded electrodes: ", electrodes_
	global data
	data = np.copy(electrodes_)
	set_all_sleeve_electrodes()
	update_sleeve_drawing()

# Save out electrodes image (electrodes representation)
# Delete this to avoid installing PIL
def save_canvas(filename, electrodes):
	ps = electrodes.postscript(colormode = 'color')
	im = Image.open(io.BytesIO(ps.encode('utf-8')))
	im.save(filename)

# Write all sleeve status to file
def write_sleeve_status_to_file(participant_ID, gesture_no, raw, tag, electrodes, data, curr_gesture, EMG_ch1, EMG_ch2, EMG_pwm, EMG_freq):
	save_canvas("data/participant_" + str(participant_ID) + "/G" + str(gesture_no) + ".jpg", electrodes)
	initialise_file(participant_ID, gesture_no, raw)
	toWrite = datetime.datetime.now(pytz.timezone('Europe/Amsterdam')).strftime("%H:%M:%S %Y-%m-%d")
	toWrite += " " + str(EMG_pwm) + " " + str(EMG_freq) + " " + str(EMG_ch1) + " " + str(EMG_ch2) + " "
	toWrite += str(curr_gesture) + "_" + tag
	write_single_line_file(toWrite)
	write_single_line_file(np.array_str(data))
	write_electrodes_to_file(participant_ID, data)

#Examine existing folders to calculate next participant ID
# Redundant here, as participant data is not currently persisted
def find_participant_ID_folder():
	dirs = next(os.walk(os.path.join(os.getcwd(), "Data/")))[1]
	print dirs
	if len(dirs) > 0:
		print "num of participants so far = " + str(len(dirs) + 1)
		last_entry = max(int(dir[12:]) for dir in dirs)
		global participant_ID
		participant_ID = last_entry+1
	else:
		participant_ID = 0
	print "participant_ID " + str(participant_ID)
	path = os.path.join(os.path.join(os.getcwd(), 'Data'), "participant_" + str(participant_ID))
	os.makedirs(path)
	return participant_ID


#Initialise output results file
def initialise_file(participant_ID, gesture_ID, calib=False, results=False):
	curr_directory = os.path.join(os.path.join(os.getcwd(), "Data"), "participant_" + str(participant_ID))
	if calib:
		file_output = "calib_gesture_" + str(gesture_ID) + ".txt"
	elif results:
		print "Creating similarity ratings file"
		file_output = "similarity_ratings.txt"
	else:
		file_output = "gesture_" + str(gesture_ID) + ".txt"
	global output_file
	output_file = open(os.path.join(curr_directory, file_output), 'w')

# Write lines to output file (initialised above)
def write_single_line_file(line):
	global output_file
	output_file.writelines(line + ' \n')

# Close output file
# MAKE SURE YOU CALL THIS, OR DATA WON'T BE SAVED
def close_file():
	global output_file
	output_file.close()

#---------------------
# Write queued data to file
# Run on individual thread
def write_to_file():
	global stop_file_writing_flag, file_write_queue
	while not stop_file_writing_flag:
		if len(file_write_queue) > 0:
			try:
				data_to_write = file_write_queue.popleft()
				output_file.writelines(data_to_write.toString())
			except:
				pass
	output_file.close()
	print "Stopping file writing"

# Add data to the write queue
def add_to_write_queue(text):
	# print "Adding to data write"
	global file_write_queue
	file_write_queue.append(text)

# Control flag for file writing thread
def start_writing_thread():
	global stop_file_writing_flag
	stop_file_writing_flag = False

# Kill the file writing thread
def kill_writing_thread():
	global stop_file_writing_flag
	stop_file_writing_flag = True

# -------------------------------------------------
# Stacked class structure for storing participant data
class StudyData:
	def __init__(self, participant):
		self.participant = participant

class Participant:
	def __init__(self, participant_no, data):
		self.ID = participant_no
		self.data = data

class GestureInstance:
	def __init__(self, data, gesture, c_data):
		self.data = data
		self.gesture = gesture
		self.calib_data = c_data

class DataInstance:
	def __init__(self, data, coordinates):
		self.data = data

		if len(data) > 0:
			# self.mean = np.mean(data) if np.mean(data) > 0.0 else 0.0
			#Root mean square
			self.mean = np.sqrt(np.mean(np.square(data)))
			# self.mean = (reduce(lambda x, y: x*y, data))**(1.0/len(data))
			self.std = np.std(data) # if np.std(data) > 0.0 else 0.0
			self.min = min(data)
			self.max = max(data)
			self.var = np.var(data)
			self.median = np.median(data)
		else:
			self.mean = 0
			self.std = 0
			self.min = 0
			self.max = 0
			self.var = 0
			self.median = 0

		#coordinates
		self.coords = coordinates

def butter_filter(datalist):
    """ Filters the data using IIR butterworth filter

        Description:
            Digital filter which returns the filtered signal using butterworth
            5th order low pass design. The cutoff frequency is 0-35Hz with 100Hz
            as sampling frequency.
        Input:
            ECGdata -- list of integers (ECG data)
        Output:
            lfilter(b,a,ECGdata)-- filtered data along one-dimension with IIR
                                      butterworth filter
    """
    fs = 200.00
    fHigh = 50.00
    fLow = 5.00
    N=4
    [b,a]=sg.butter(N,[fLow/fs, fHigh/fs], btype='band')
    global filtered
    #IIR filter
    return sg.filtfilt(b,a,datalist)

#Read data in from file
def read_sensor_data(participant_ID, ID, min_row, max_row):
	studyData = []
	data_path = os.path.join(os.getcwd(), "Data")
	file_name = "gesture_" + str(ID) + ".txt"
	file_path = os.path.join(data_path, "participant_" + str(participant_ID))
	try:
		f = open(os.path.join(file_path, file_name), 'r')
	except:
		return

	print "Reading: ", file_path, file_name
	data = f.readlines()
	datalist = []
	dataVals = []
	calibVals = []
	dataInstances = []
	for idx, line in enumerate(data):
		if idx == 0:
			continue
		if line != "\n":
			if "Gesture" in line:
				gesture = line.split(" ")[1]
				print "gesture = " + gesture
			elif "EMG" in line:

				splitVals = line.split(" ")
				coordinates = [int(vals) for vals in splitVals[1:5]]
				if coordinates[0] < min_row or (coordinates[0] > max_row or coordinates[2] > max_row):
					continue
				if coordinates[3] < (coordinates[1] - 1) or coordinates[3] > (coordinates[1] + 1):
					if (coordinates[3] == 5 and coordinates[1] == 0) or (coordinates[3] == 0 and coordinates[1] == 5):
						pass
					else:
						continue

				del splitVals[0:5]
				for vals in splitVals:
					vals_new = vals.strip(',').replace('[', '').replace(']','')
					try:
						datalist.append(int(vals_new))
					except:
						pass

				datalist_butter = butter_filter(datalist)

				if idx < 5 or idx > len(data)-4:
					calibVals.append(DataInstance(datalist_butter, coordinates))
				else:
					dataVals.append(DataInstance(datalist_butter, coordinates))

				datalist = []
			else:
				splitVals = line.split(" ")
				del splitVals[-1]
				dataVals.append(DataInstance([int(i) for i in splitVals]))
				print dataVals
				if len(dataVals) == 4:
					dataInstances.append(GestureInstance(dataVals, gesture))
					dataVals = []
					gesture = ""

	#Temporary test
	dataInstances.append(GestureInstance(dataVals, "EMG", calibVals))
	participant = Participant(ID, dataInstances)
	global studyData
	studyData.append(StudyData(participant))

