\# Vision Captioning Module — Raspberry Pi 5 Assistive System



This project provides an \*\*offline vision-to-speech pipeline\*\* for assistive navigation and situational awareness.  

It captures images from a webcam, generates descriptive captions locally using \*\*BLIP-base\*\*, and reads them aloud using \*\*Piper TTS\*\* with natural humanlike speech.



---



\## ✨ Features



\- 🧠 \*\*Offline BLIP-base model\*\* (`Salesforce/blip-image-captioning-base`)  

&nbsp; Generates natural-language descriptions of captured scenes.  

\- 🔊 \*\*Piper TTS (Amy-medium voice)\*\*  

&nbsp; Converts text into realistic speech, optimized for PipeWire + Bluetooth output.  

\- 💻 \*\*Modular Python package\*\* (`vision\_caption/`)  

&nbsp; Clean structure — easy to extend with sensors, voice commands, or asynchronous triggers.  

\- 🎧 \*\*Bluetooth audio\*\*  

&nbsp; Works smoothly with JBL or similar Bluetooth headsets on Pi OS (Bookworm).  

\- ⚙️ \*\*Fully offline\*\*  

&nbsp; No cloud dependencies, no API calls — perfect for mobile and privacy-focused applications.



---



\## 📁 Directory Structure





