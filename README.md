## What is pulseaudio nuc server
Its linux distribution which designed for intel nuc.\
With only purpose to serve audio over network.

It has pulseaudio server installed which is responsible for audio streaming over network
Here is an example of one of the possible setups:

<img src="https://github.com/danilovsergei/pulseaudio_nuc_server/blob/master/wiki/images/pulseaudio-server.png" width="70%" height="70%">

Some of the main features:
1. It automatically starts Pulseaudio server right after given ISO boots on nuc.
#TODO: add an explanation for network configuration
2. Pulseaudio server already configured to:
   - Announce itself via [avahi zeroconf](https://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/User/Network/#index1h1)\
     All clients will be able to see and redirect sound output. Pulseaudio server will look somewhat like that over network:\
     <img src="https://github.com/danilovsergei/pulseaudio_nuc_server/blob/master/wiki/images/avahi_clients.png" width="30%" height="30%">
   - Defaults output through 5.1 hdmi on nuc. Assumption is nuc connected to some multichannel receiver as shown on the diagram.\
   - Designed to receive uncompressed multichannel audio
3. Works both over wifi or ethernet connection depending on provided configuration
