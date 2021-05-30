# TelegramSTT
Annoyed by that one friend who sends you voice messages, even though you strongly prefer text?  
This bot is here to help by using Mozillas DeepSpeech to turn speech to text!

## Installation
While working natively just fine, I strongly recommend unsing `docker`.
images are provided [by me](https://hub.docker.com/repository/docker/mawalla/telegram-stt).
Either use `docker run mawalla/telegramstt` or even better: use `docker-compose`, an example file is included!
for `docker run` you may wanna add a mapping for the path `/auth` within the container since it makes sense to keep those files persistent. For `docker-compose`, you wanna modify the path in the example file.

If running natively, you may need to install the dependencies using `pip install -r requirements.txt`, preferredly in a [venv](https://docs.python.org/3/library/venv.html).
With those in place, you can run it with `python main.py`
This application is currently targetting Python 3.9

## Configuration
Some env variables can/need to be set for this app to correctly function
- `BOTTOKEN` needs to be set, it can be acquired using @BotFather within Telegram.
- `ADMINNAME` optional, but strongly recommended so users get a relevant person to contact in case of errors. Set your telegram username together with the @ coming before it.
- `STTADDRESS` optional, but required for standalone installations. sets the address of your Mozilla DeepSpeech server. Defaults to my `docker-compose` address. usually something like `http://deepspeech.address/stt`
- `AUTHPATH`  optional, modifies the path where authentification files are stored, makes sense to modify for standalone installations. Defaults to /auth as per docker image.
- `FILEPATH`  optional, modifies the path where temporary files for processing are stored, makes senseto modify for standalone installations. Defaults to /files as per docker image.

## On the DeepSpeech image
Unless you already got DeepSpeech running, you may wanna use my `docker-compose` file, or use the [deepspeech-server image](https://hub.docker.com/repository/docker/mawalla/deepspeech-server) I made (loosely based on [romainsah/deepspeech-server](https://hub.docker.com/r/romainsah/deepspeech-server)). 
Setting it up is pretty simple. Just adjust the mapping pointing to `/opt/deepspeech` to any suitable path on your server.
In there you'll need you model (usually a `.scorer` and `.pbmm` file) and a file named `config.json`. In there you'll only need to set:
```
{
  "deepspeech": {
    "model" :"/opt/deepspeech/output_graph.pbmm",
    "scorer" :"/opt/deepspeech/kenlm.scorer",
    "beam_width": 500,
    "lm_alpha": 0.931289039105002,
    "lm_beta": 1.1834137581510284
  }
}
```
`beam_width`, `lm_alpha` and `lm_beta` may need to be modified according to you model, the path containing `/opt/deepspeech/...` should be kept like this due to the docker mapping, except for the actual file name, which needs to be adjusted for your used model.
Furthermore, other settings can be made here too. More on that[here](https://github.com/MainRo/deepspeech-server).

## Usage
With the app running, you'll need to register users, like yourself.
Just use the `/register` command when using the bot. it will modify `/auth/register.json`.
In there you'll find the user id and some identifying info for the user. Put the user id into `whilelist.json` to allow or `blacklist.json` to deny access, depending on your choice. Finally you can remove the entry for the user from `register.json`. While doing all this, definitely keep the json structure intact!

Each time the `/register` command is run, the bot will re-read the files, updating its knowledge on the values. It also informs the user on the registration status (if they've already gotten processed and whether they've been put on the white- or blacklist).

When done its time to send voice messages to the bot! It will process the audio data, send it to DeepSpeech and then come back to you with the text.
