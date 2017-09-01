We have been researching auto-calibration techniques for high-density Electric Muscle Stimulation.

In this repository, you will find the implementation details and source code of our initial prototype. 

To begin, please read the following paper:

Knibbe, J., Strohmeier, P., Boring, S., Hornbaek, K., Automatic Calibration of High Density Electric Muscle Stimulation, ACM IMWUT, September 2017.

To cut a long story short, EMS (Electric Muscle Stimulation) has two outstanding problems: (1) It is low resolution - we cannot target all muscles sufficiently to stimulate a full range of natural movement, and (2) calibration is hard. 

Typically, EMS uses pairs of large electrodes to target large muscle bodies. This enables us to control coarse movements, such as flexing the hand in and out. We believe that, in order to achieve higher resolution control (such as individual finger targeting), we need to use many smaller electrodes simultaneously. So instead of writing from 1 anode electrode to 1 cathode, we need to write from 8 anodes to 12 cathodes, or 14 anodes to 3 cathodes, or so on. This leads to another problem - calibration.

Even when only using pairs of large electrodes, calibration is a challenge. You have to find the optimal location for the electrodes and the optimal stimulation parameters. This involves placing, removing, re-placing electrodes and trial and error parameter exploration. This can easily take 5 minutes, and needs to be done per participant and per target movement. So, if you want to build an interactive system with only 4 movements, you are looking at 20 minutes of calibration prior to every use. 

If we now cover the arm in electrodes, as we intend to, the calibration process becomes increasingly complex - we now have to determine what combination of our electrodes to use for any movement. This explodes the possible unique combination of electrodes to 3^^n - 2^^n+1 + 2 (where n is the total number of electrodes). Clearly this is infeasible to test. 

So, we use EMG (electromyography) to read muscle activity between all electrodes and use this to inform our stimulation patterns with EMS. This means that the user manually performs a pose they would like to use, while we read EMG data, then we can use EMS to get them to re-perform that pose. 

In this repository, you will find the details of our prototype system for exploring this. The prototype includes a sports sleeve of 60 electrodes and the associated switching circuitry. We also include all of the control software.