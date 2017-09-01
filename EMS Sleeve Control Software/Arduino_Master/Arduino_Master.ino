//Controlling Mux through library:
//https://github.com/federico-galli/Arduino-dual-i2c-potentiometer-DS1803
//Also needs wire
#include <DS1803.h>
#include <Wire.h>

//2 operating states - EMG, (EMG collect), EMS
boolean gather_EMG = false;
boolean gather_EMG_collect = false;
boolean gather_EMG_specific = false;
boolean stim_EMS = false;

//-------------- EMG Variables
//switch power to EMGs
int power_EMG_switch = A15;

//EMG relay switches
int signal_EMG_1_pos_switch = 2;
int signal_EMG_1_neg_switch = 3;
int signal_EMG_2_pos_switch = 4;
int signal_EMG_2_neg_switch = 5;

//Read EMG input from
int signals_EMG[] = {A1, A2}; 

//Data array for storing EMG values
int readings_EMG[2][200];
int readings_EMG_count = 0;

//-------------- EMS Variables
//Switch power to EMS
int power_EMS_switch = 6;
int signal_EMS_1_pos_switch = 7;
int signal_EMS_1_neg_switch = 8;
int signal_EMS_2_pos_switch = 9;
int signal_EMS_2_neg_switch = 10;

//DigiPot pot_width(pulse width, frequency), DigiPot pot_chans(Chan 1, +/-),(Chan 2, +/-)
DS1803 pot_width(0x2C);
//DS1803 pot_width_2(0x2E);
DS1803 pot_chans(0x28);

//Active channel tracker
//Ensuring opposite channel is active before running EMG
int active_channels[] = {0,0,0,0};

//4 inputs per sleeve row
//Electrode data class
struct electrode{
	int chan;
};

//Sleeve row data class
struct electrode_row{
	electrode electrodes[6];
	//latch, clock, data, outputEnable
	int shift_pins[4];
};

//10 rows of electrodes
electrode_row sleeve[10];

//Circuit Debug Variables
int EMS_LED = A14;
int EMG_LED = A13;

//Debug print buffer
char buffers[16];

void setup(){
	Serial.begin(38400);

	int curr_digi_pin_count = 11;

	//Sleeve Creation
	for (int i = 0; i < 10; i++) {
		//Set all electrodes off to start with
		for (int j = 0; j < 6; j++) {
			sleeve[i].electrodes[j].chan = -1;
		}

		for (int j = 0; j < 4; j++) {
			sleeve[i].shift_pins[j] = curr_digi_pin_count;

			curr_digi_pin_count += 1;
			pinMode(sleeve[i].shift_pins[j], OUTPUT);

			if (curr_digi_pin_count == 19) curr_digi_pin_count += 3;
		}
	}
	write_output_enable(true);

	//EMG Setup
	pinMode(power_EMG_switch, OUTPUT);

	pinMode(signal_EMG_1_pos_switch, OUTPUT);
	pinMode(signal_EMG_1_neg_switch, OUTPUT);
	pinMode(signal_EMG_2_pos_switch, OUTPUT);
	pinMode(signal_EMG_2_neg_switch, OUTPUT);
	for (int i = 0; i < 2; i++) {
		pinMode(signals_EMG[i], INPUT);
	}

	//EMS Setup
	pinMode(signal_EMS_1_pos_switch, OUTPUT);
	pinMode(signal_EMS_1_neg_switch, OUTPUT);
	pinMode(signal_EMS_2_pos_switch, OUTPUT);
	pinMode(signal_EMS_2_neg_switch, OUTPUT);
	pinMode(power_EMS_switch, OUTPUT);
	pot_chans.setPot(0, 0);
	pot_chans.setPot(0, 1);
	pot_width.setPot(0,0);
	pot_width.setPot(0,1);
	//pot_width_2.setPot(0,0);
	//pot_width_2.setPot(0,1);

	//Circuit Debug Setup
	pinMode(EMS_LED, OUTPUT);
	pinMode(EMG_LED, OUTPUT);
}

void loop() {
	//if running EMG, then wait for finish, else wait for new input
	if (gather_EMG_collect == true) {
//		unsigned long StartTime = micros();
		run_EMG_read_multi();
//		unsigned long CurrentTime = micros();
//		unsigned long ElapsedTime = CurrentTime - StartTime;
//                Serial.println(ElapsedTime);
	}
	else {
		readInputLine();
		//update_sleeve_row_all();
	}
}

//Read analog for all EMG signals up to read_row_max_EMG
void run_EMG_read_single(){
 	while (readings_EMG_count < 120){
		readings_EMG[0][readings_EMG_count] = analogRead(signals_EMG[0]);
		readings_EMG_count++;
		//delay(2);
  	}
	report_EMG_to_python_single();
	gather_EMG_collect = false;
	clear_signal_selection();
	readings_EMG_count = 0;
}

//Write completed columns to serial, for python
void report_EMG_to_python_single() {
	Serial.print("EMG ");
	for (int i = 100; i < 120; i++)
	{
		Serial.print(readings_EMG[0][i]);
		Serial.print(" ");
	}
	Serial.println();
}

//Read analog for all EMG signals up to read_row_max_EMG
void run_EMG_read_multi(){
//        unsigned long StartTime = micros();
 	while (readings_EMG_count < 50){
		readings_EMG[0][readings_EMG_count] = analogRead(signals_EMG[0]);
		readings_EMG[1][readings_EMG_count] = analogRead(signals_EMG[1]);
		readings_EMG_count++;
		delay(1);
  	}
//        unsigned long CurrentTime = micros();
//        unsigned long ElapsedTime = CurrentTime - StartTime;
//        Serial.println(ElapsedTime);
	report_EMG_to_python_multi();
	gather_EMG_collect = false;
//	clear_signal_selection();
	readings_EMG_count = 0;
}

//Write completed columns to serial, for python
void report_EMG_to_python_multi() {
	for (int j = 0; j < 2; j++){
		String toPrint;
		//toPrint = "EMG ";
		Serial.print("EMG ");
                Serial.print(j);
                Serial.print(" ");
		for (int i = 20; i < 50; i++)
		{
//			toPrint += readings_EMG[j][i];
//			toPrint += " ";
			Serial.print(readings_EMG[j][i]);
			Serial.print(" ");
		}
		Serial.println();
	}
}

//Read control signals from serial
//Signals:
//3 = Off/Neutral Mode
//4 = read EMG Mode (specific electrodes)
//5 = run EMS Mode (random walk)
//returns true (if read), false (if unavailable)
void readInputLine(){
	if (Serial.available()) {
		int commandValue = Serial.parseInt();
		char labelValue = Serial.read();

		//Serial.print(commandValue);
		//Serial.println(labelValue);

		//Deal with main flag commands and enable/disable switches
		if (commandValue < 7 && labelValue == 'c') {
			reset_flags();
			switch (commandValue) {
				case 1 :
					break;
				case 2:
					break;
				case 3:
					clear_signal_selection();
					break;
				case 4: 
					gather_EMG = true;
					clear_signal_selection();
					digitalWrite(power_EMG_switch, HIGH);
					digitalWrite(signal_EMG_1_pos_switch, HIGH);
					digitalWrite(signal_EMG_1_neg_switch, HIGH);
					digitalWrite(signal_EMG_2_pos_switch, HIGH);
					digitalWrite(signal_EMG_2_neg_switch, HIGH);
					digitalWrite(EMG_LED, HIGH);
					break;
				case 5: 
					clear_signal_selection();
					stim_EMS = true;
					pot_chans.setPot(0, 0);
					pot_chans.setPot(0, 1);
					pot_width.setPot(0,0);
					pot_width.setPot(0,1);
					//pot_width_2.setPot(0,0);
					//pot_width_2.setPot(0,1);
					digitalWrite(power_EMS_switch, HIGH);
					digitalWrite(signal_EMS_1_pos_switch, HIGH);
					digitalWrite(signal_EMS_1_neg_switch, HIGH);
					digitalWrite(signal_EMS_2_pos_switch, HIGH);
					digitalWrite(signal_EMS_2_neg_switch, HIGH);
					digitalWrite(EMS_LED, HIGH);
					break;
				default:
					break;   
			}
		}

		//Get values to configure EMS or control sleeve
		//Format (n = int variable)
		//-----'nr nt ni' = row, col, channel
		//-----'np' = pulse width, 'nz' = frequency
		//-----'na' = chan 1 amplitude, 'ng' = chan 2 amplitude
		if (gather_EMG || stim_EMS) {

			switch (labelValue) {
				case 'r':
                {
					int colValue = Serial.parseInt();
					char colLabel = Serial.read();

					int chanValue = Serial.parseInt();
					char chanLabel = Serial.read();

					//Set electrode channel value
					if (labelValue == 'r' && colLabel == 't' && chanLabel == 'i') {
						if (chanValue < 0){
							active_channels[sleeve[commandValue].electrodes[colValue].chan] -= 1;
						}
                                                
						sleeve[commandValue].electrodes[colValue].chan = chanValue;

						if (chanValue >=0){
							active_channels[chanValue] += 1;
						}
					}

					//Update the whole sleeve row
					update_sleeve_row(commandValue);

					if (chanValue >= 0 && gather_EMG && check_opposite_channel(chanValue)) gather_EMG_collect = true;

					break;
				}
				case 'p' :
				{
					int freqValue = Serial.parseInt();
					int freqLabel = Serial.read();

					if (freqLabel == 'z') {
						pot_width.setPot(int(commandValue), 0);
						pot_width.setPot(int(freqValue), 1);
						//pot_width_2.setPot(int(commandValue), 0);
						//pot_width_2.setPot(int(freqValue), 1);
					}
					break;
				}
				case 'a' :
				{
					int chan2Value = Serial.parseInt();
					int chan2Label = Serial.read();

					if (chan2Label == 'g') {
						pot_chans.setPot(commandValue, 0);
						pot_chans.setPot(chan2Value, 1);
					}
					break;
				}
				case 'f' :
					set_whole_sleeve_row(commandValue, false);
					break;
				case 'u' :
					set_whole_sleeve_row(commandValue, true);
					break;
				default:
					break;
			}
		}
	}
}

void update_sleeve_row_all(){
  for (int uarow = 0; uarow < 10; uarow++){
    //Serial.print("Updating row ");  
    //Serial.println(uarow);  
    if (check_row_active(uarow)) update_sleeve_row(uarow);
  }
}

boolean check_row_active(int curr_row){
  for (int i = 0; i < 6; i++) {
    if (sleeve[curr_row].electrodes[i].chan >= 0){
      return true;
    }
  }
  return false;
}

//Not check opposite, check all
boolean check_opposite_channel(int chan){
	bool all_active = true;
	for (int i = 0; i < 4; i++) {
		if (active_channels[i] == 0) all_active = false;
	}
	return all_active;
  //int target_chan = -1;
  //target_chan = (chan % 2 == 0 ? chan + 1 : chan - 1);
  //return (active_channels[target_chan] > 0);
}

void set_whole_sleeve_row(int row, bool on_off){
	byte vals[3];

	for (int i = 0; i < 3; i++) vals[i] = 0;

	for (int i = 0; i < 6; i++) {
		if (on_off) bitSet(vals[int(i/2)], on_off + ((i%2)*4));
	}

	digitalWrite(sleeve[row].shift_pins[0], LOW);
	for (int i = 2; i >= 0; i--) {
		//Serial.println(vals[i]);
		shiftOut(sleeve[row].shift_pins[2], sleeve[row].shift_pins[1], MSBFIRST, vals[i]);
	}
	//Serial.println("*************");
	digitalWrite(sleeve[row].shift_pins[0], HIGH);
	digitalWrite(sleeve[row].shift_pins[3], LOW);
}

void update_sleeve_row(int row){
	byte vals[3];

	for (int i = 0; i < 3; i++) vals[i] = 0;

	//loop through all electrodes and set byte values
	for (int i = 0; i < 6; i++){
		if (sleeve[row].electrodes[i].chan >= 0) {
			bitSet(vals[int(i/2)], sleeve[row].electrodes[i].chan + ((i%2)*4));
		}
	}

	digitalWrite(sleeve[row].shift_pins[0], LOW);
	for (int i = 2; i >= 0; i--) {
		//Serial.println(vals[i]);
		shiftOut(sleeve[row].shift_pins[2], sleeve[row].shift_pins[1], MSBFIRST, vals[i]);
	}
	//Serial.println("*************");
	digitalWrite(sleeve[row].shift_pins[0], HIGH);
	digitalWrite(sleeve[row].shift_pins[3], LOW);
}

void clear_signal_selection(){
	for (int row = 0; row < 10; row++) {
		if (check_row_active(row)){
			for (int col = 0; col < 6; col++) {
    			sleeve[row].electrodes[col].chan = -1;
    		}
    		update_sleeve_row(row);
        }
	}
	for (int chans = 0; chans < 4; chans++){
		active_channels[chans] = 0;
	}
}

void write_output_enable(boolean enable){
  for (int row = 0; row < 10; row++){
    for (int col = 0; col < 6; col++){
      digitalWrite(sleeve[row].shift_pins[3], enable);
    }
  }
}

void reset_flags(){
	gather_EMG = false;
    gather_EMG_collect = false;
	digitalWrite(power_EMG_switch, LOW);
	digitalWrite(signal_EMG_1_pos_switch, LOW);
	digitalWrite(signal_EMG_1_neg_switch, LOW);
	digitalWrite(signal_EMG_2_pos_switch, LOW);
	digitalWrite(signal_EMG_2_neg_switch, LOW);
	stim_EMS = false;
	pot_chans.setPot(0, 0);
	pot_chans.setPot(0, 1);
	pot_width.setPot(0,0);
	pot_width.setPot(0,1);
	//pot_width_2.setPot(0,0);
	//pot_width_2.setPot(0,1);
	digitalWrite(power_EMS_switch, LOW);
	digitalWrite(signal_EMS_1_pos_switch, LOW);
	digitalWrite(signal_EMS_1_neg_switch, LOW);
	digitalWrite(signal_EMS_2_pos_switch, LOW);
	digitalWrite(signal_EMS_2_neg_switch, LOW);
	digitalWrite(EMG_LED, LOW);
	digitalWrite(EMS_LED, LOW);
}
