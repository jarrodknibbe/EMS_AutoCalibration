The hardware schematics included here are for an initial prototype to support our work. 

Each circuit board consists of:
- 3 shift registers SN74HC595N
- 24 solid state relays CPC1218Y

This enables switching control over 6 electrodes. As we have 60 electrodes in our prototype, we stacked 10 of the boards. The boards are designed to stack into a tower using alternating headers. 

Besides our custom circuit boards, we also use 1 off-the-shelf EMS unit (Med-Fit 1, though anything similar would do) and 2 EMG devices (Backyard Brains Muscle Spiker Shields). We remove the manual potentiometers from the EMS device and replace them with digital potentiometers (DS1803-050). This gives digital control over the amplitude, pulse width and frequency of the stimulation signal. 

All circuitry connects to an Arduino Mega. This cannot provide enough current to support the signal switching board, so we use a second Arduino Mega. This could also be provide by batteries, a power suplly, etc. Both of the Muscle Spiker Shields (for EMG) take their own Arduino Uno. 


There are undoubtedly optimisations and improvements that can be made. Current limitations or points for consideraion:

1. Our design did not focus on a small form factor, so ends up being quite large (as can be seen in the figures in the associated paper). 
2. We have reason to believe that our choice of relay (CPC1218Y) was also not sufficient for switching all possible signals out of our EMS device (the voltage can go above the limit of the relay). We never noticed any failure behaviour, but a CPC1215 may be more appropriate. I think, if I were to make the adjustments for a different relay, I would consider smaller surface mount relay options, to reduce the overall form factor. 
3. The EMG read process is too slow. The switching of the relays introduces noise to the EMG signal, requiring waiting between switching and reading. This means that our device can only read information for poses, not dynamic gestures. In the future, more EMG devices are needed to increase the speed of the reading cycle. 
4. The resolution of the Muscle Spiker Shields is too low. A higher-bit ADC is required to get the most out of the signal.

