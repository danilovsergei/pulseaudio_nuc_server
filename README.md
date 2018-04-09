## What is pulseaudio nuc server
It's linux distribution which designed for intel nuc.\
And its only purpose is to server audio over network.

It has pulseaudio server installed which is responsible for audio streaming over network
Here is an example of one of the possible setups:

<img src="https://github.com/danilovsergei/pulseaudio_nuc_server/blob/master/wiki/images/pulseaudio-server.png" width="70%" height="70%">

Distribution has features:
1. It automatically starts Pulseaudio server right after given ISO boots on nuc.
#TODO: add an explanation for network configuration
2. Pulseaudio server already configured to:
   - Announce itself via [avahi zeroconf]     (https://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/User/Network/#index1h1). All clients will be able to see    and redirect sound output.
  pulseaudio server will look somewhat like that over network:
  <img src="https://github.com/danilovsergei/pulseaudio_nuc_server/blob/master/wiki/images/avahi_clients.png" width="30%" height="30%">
   - default output through 5.1 hdmi on nuc. Assumption is nuc connected to some multichannel receiver as shown on the diagram.
   


