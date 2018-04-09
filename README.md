## What is pulseaudio nuc server
Its Gentoo based linux distribution for intel nuc with only purpose to stream audio over network.

It has pulseaudio server installed which is responsible for audio streaming over network\
Here is an example of one of the possible setups:

<img src="https://github.com/danilovsergei/pulseaudio_nuc_server/blob/master/wiki/images/pulseaudio-server.png" width="70%" height="70%">

## Main features:
1. Works both over wifi or ethernet connection depending on provided configuration
2. Designed for uncompressed multichannel audio
3. Does not require application support to stream on client side(like chromecast). Sound redirected on system level.
4. Just plug'n'play after installation. Nuc starts all pulseaudio server and all services automatically on boot.
5. Distribution is hard to break. Its just one readonly ISO file fully loaded to ram on boot with write overlayfs on top.
   Which also means its very simple to upgrade

5. Pulseaudio server already configured to:
   - Announce itself via [avahi zeroconf](https://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/User/Network/#index1h1)\
     All clients will be able to see and redirect sound output. Pulseaudio server will look somewhat like that over network:\
     <img src="https://github.com/danilovsergei/pulseaudio_nuc_server/blob/master/wiki/images/avahi_clients.png" width="30%" height="30%">
   - Default output through 5.1 hdmi on nuc. Assumption is nuc connected to some multichannel receiver as shown on the diagram.
   
## Motivation to create
As mentioned in the features I needed to play uncompressed multichannel audio from my laptop.\
And only hdmi port which can do it already occupied by monitor.
Solution is to use dedicated Intel nuc which is cheap enough to serve as audio card over network.

Besides that given setup adds more features like streaming over wifi and from other devices.

Intel nuc choosen due to
* perfect 5.1 audio support
* no need to cross compile for arm. I just build regular x86 64bit image.

## Downloads

## How to install
