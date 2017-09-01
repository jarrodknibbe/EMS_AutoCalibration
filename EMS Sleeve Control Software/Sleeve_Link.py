
#--------------------
#Handles sending data to and from the arduino
#Coordinates both EMG and EMS
#--------------------

#Import libraries
import serial
import time
import threading
from collections import deque
from File_Link import add_to_write_queue

#Flag controlling EMS 'ramp'
#EMS starts low and increases up to target level (Reduces muscle jarring)
stop_EMS_ramp = False

#Connect to Sleeve over serial
try:
	global serialController
	print "Trying to connect to Controller"
	serialController = serial.Serial('/dev/tty.usbmodem1411', 38400, timeout=None)
	print "Connected to Controller"
	# serialController.flush()
	# serialController.flush()
except:
	print "Controller missing"
time.sleep(1)

#Disconnect from sleeve - eases connection the next time
def disconnect_EMS():
	try:
		global serialController
		serialController.close()
		print "Disconnected EMS"
	except:
		print "Cannot disconnect EMS"

#Track number of active electrodes, only turn on EMS if > 2
num_active_electrodes = 0

#Fixed variables for EMG pwm, freq, (ch1 / ch2) amplitude
EMG_pwm = 5
EMG_freq = 5
EMG_ch1 = 5
EMG_ch2 = 5

#Track status of EMS stimulation
EMS_active = False

#Flag for controlling serial read thread
stop_serial_reading_flag = False

#data storage instance
class DataInstance:
	def __init__(self, data_type, dev_id, pos_row, pos_col, neg_row, neg_col, data):
		self.type = data_type
		self.dev = dev_id
		self.pos_row = pos_row
		self.pos_col = pos_col
		self.neg_row = neg_row
		self.neg_col = neg_col
		self.data = list(data)

	def toString(self):
		data_string = str(self.type) + " " + str(self.dev) + " " + str(self.pos_row) + " " + str(self.pos_col) + " " + str(self.neg_row) + " " + str(self.neg_col) + " "
		data_string += str(self.data)
		data_string += " \n"
		return data_string

#-----------------------------------------------
#------------EMS Controls-----------------------

#Return amplitude values
def get_amplitudes():
	return EMG_ch1, EMG_ch2

#Set amplitude values
def set_amplitude(_EMG_ch1, _EMG_ch2):
	EMG_ch1 = _EMG_ch1
	EMG_ch2 = _EMG_ch2

#Return freq, pwm values
def get_freq_pwm():
	return EMG_freq, EMG_pwm

#Set freq, pwm values
def set_freq_pwm(_freq, _pwm):
	freq = _freq
	pwm = _pwm

#Send commands via serial
#Input:
#	controller - true = controller, false = sleeve
#	val = string of commands
def send_command(controller, val):
	global serialController
	if controller and 'serialController' not in globals():
		print "Serial controller not connected " + str(val)
		return

	if controller:
		print "sending controller: " + str(val)
		ret_val = serialController.write(val)

#Set a specific electrode to a channel
#Input:
#	x = column
#	y = row
#	z = channel
def set_sleeve_electrodes(x, y, z):
	command = str(y) + "r " + str(x) + "t " + str(int(z)-1) + "i"
	send_command(True, command)

#Set all electrodes based on 'data' array
#'data' array holds representation of sleeve electrodes and channels
def set_all_sleeve_electrodes(data):
	for locs in np.argwhere(data > 0.):
		set_sleeve_electrodes(locs[1], locs[0], data[locs[0]][locs[1]])

#send controller frequency and pwm values
def set_controller_freq_pwm(EMG_pwm, EMG_freq):
	command = str(EMG_pwm) + "p " + str(EMG_freq) + "z"
	send_command(True, command)

#send controller channel 1 and channel 2 amplitude values
def set_controller_amplitude(EMG_ch1, EMG_ch2):
	command = str(EMG_ch1) + "a " + str(EMG_ch2) + "g"
	send_command(True, command)

#Flip off EMS and re-enable
def reset_connection():
	command = "3c"
	send_command(True, command)

	time.sleep(1)
	command = "5c"
	send_command(True, command)
	EMS_active = True

	set_all_sleeve_electrodes()
	set_controller_amplitude()
	set_controller_freq_pwm()

#Set parameters to 0 and disable EMS when exiting
def _quit(root, raw):
	set_controller_amplitude(0,0)
	command = "3c"
	send_command(True, command)
	disconnect_EMS()

#--------------------------------------------------

#--------------------------------------------------
#---------------EMG Controls-----------------------

#Hold coordinate data to be read
#Add electrode coordinates to queue, then pop and pair to read values
#in separate thread
coordinate_data_queue = deque()

#Flag to stop reading process
stop_serial_reading_flag = False

#Read EMG values from Arduino
def read_EMG_from_serial_controller():
	vals = serialController.readline()

	#handle timeout
	if len(vals)==0:
		return 0, []

	# print vals

	splitVals = vals.split(" ")

	if not len(splitVals) == 33:
		return 0, 0, []

	type_ID = splitVals[0]
	dev_ID = splitVals[1]
	del splitVals[0]
	del splitVals[0]
	del splitVals[-1]
	readings = []
	for val in splitVals:
		try:
			readings.append(int(val))
		except:
			readings.append(0)
			print "Error in values: ", splitVals
	#print "readings = " + str(readings)
	return type_ID, dev_ID, readings

#Handle serial reading process
#Read from serial line, grab results, add to file write queue
def process_serial_data():
	global stop_serial_reading_flag, coordinate_data_queue
	while not stop_serial_reading_flag:

		if len(coordinate_data_queue) > 0:
			type_ID, dev_ID, readings = read_EMG_from_serial_controller()

			#handle timeout
			if type_ID == 0 and not readings:
				continue

			try:
				if type_ID != "EMG":
					type_ID = "EMG" 
				coordinates = coordinate_data_queue.popleft()
				# store_average_readings(type_ID, readings, coordinates)
				out = DataInstance(type_ID, dev_ID, coordinates[0], coordinates[1], coordinates[2], coordinates[3], readings)
				add_to_write_queue(out)
			except IOError as e:
				print "I/O error({0}): {1}".format(e.errno, e.strerror)
				print "Failed ", readings
				pass
			#print "receiving ", str(coordinates), ": ", readings
			print "receiving ", str(coordinates) #, dev_ID# readings
		
	print "*" * 20
	print "Stopping serial read"

def start_reading_thread():
	global stop_serial_reading_flag
	stop_serial_reading_flag = False

def kill_reading_thread():
	global stop_serial_reading_flag
	stop_serial_reading_flag = True

def flush_buffers():
	serialController.reset_input_buffer()
	serialController.reset_output_buffer()

#--------------------------------------------------
