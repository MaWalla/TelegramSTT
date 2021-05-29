import json
import logging
import os
import threading

from textwrap import dedent

import requests as requests
from pydub import AudioSegment

from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


class TelegramSTT:

    def __init__(self):
        token = os.getenv('BOTTOKEN')
        if not token:
            logger.error('please add your bot token as BOTTOKEN env variable.')
            exit(1)

        auth_path = os.getenv('AUTHPATH', '/auth/')
        if not os.path.exists(auth_path):
            logger.warning(f'File path {auth_path} does not exist! Attempting to create it.')
            os.makedirs(auth_path, exist_ok=True)

        self.file_path = os.getenv('FILEPATH', '/files/')
        if not os.path.exists(self.file_path):
            logger.warning(f'File path {self.file_path} does not exist! Attempting to create it.')
            os.makedirs(self.file_path, exist_ok=True)

        self.stt_address = os.getenv('STTADDRESS', 'http://172.13.13.3:8080/stt')

        self.blacklist_path = os.path.join(auth_path, 'blacklist.json')
        self.blacklist = self.read_json(self.blacklist_path)
        self.whitelist_path = os.path.join(auth_path, 'whitelist.json')
        self.whitelist = self.read_json(self.whitelist_path)

        self.register_path = os.path.join(auth_path, 'register.json')
        self.registerlist = self.read_json(self.register_path)

        self.admin_name = os.getenv('ADMINNAME')
        if not self.admin_name:
            logger.warning('ADMINNAME env var not set, can\'t refer to you in case of errors.')

        updater = Updater(token)
        dispatcher = updater.dispatcher

        dispatcher.add_handler(CommandHandler('start', self.start))
        dispatcher.add_handler(CommandHandler('help', self.help))
        dispatcher.add_handler(CommandHandler('register', self.register))
        dispatcher.add_handler(CommandHandler('privacy', self.privacy))

        dispatcher.add_handler(MessageHandler(Filters.voice | Filters.audio & ~Filters.command, self.audio))

        updater.start_polling()
        updater.idle()

    @staticmethod
    def start(update: Update, _: CallbackContext):
        user = update.effective_user
        response_string = fr'''
            Hi {user.mention_markdown_v2()}\.
            if not done already, use /register
            to request access to this bot\!\
            
            See /privacy for privacy information\.
        '''
        update.message.reply_markdown_v2(
            dedent(response_string),
            reply_markup=ForceReply(selective=True),
        )

    @staticmethod
    def help(update: Update, _: CallbackContext):
        response_string = f'''
            You must be registered (using /register) in order to use this bot.
            An admin will process your request eventually and confirm it.
            Please note that your name will be accessible to the admin.
            
            Once done, you can just send/forward voice messages here
            and the bot will try to process them, replying with the result.
            You must keep the messages shorter than 5 minutes though.
            
            See /privacy for privacy information.
        '''
        update.message.reply_text(dedent(response_string))

    @staticmethod
    def privacy(update: Update, _: CallbackContext):
        response_string = f'''
            This bot possibly handles your private information.
            for speech recognition, a self hosted Mozilla DeepSpeech
            is used. This means that no data leaves the server.
            
            Your text responses may be logged by DeepSpeech however
            and may be seen by the server owner/admins.
            
            This normally isn't the case though.
        '''
        update.message.reply_text(dedent(response_string))

    def register(self, update: Update, _: CallbackContext):
        response_string = ''
        user = update.effective_user
        self.blacklist = self.read_json(self.blacklist_path)
        self.whitelist = self.read_json(self.whitelist_path)
        self.registerlist = self.read_json(self.register_path)

        register_ids = [entry.get('id') for entry in self.registerlist]

        if user.id not in [*self.blacklist, *self.whitelist, *register_ids]:
            response_string = f'''
                Your information (Telegram ID, Telegram username)
                has been recorded and can now be processed by an admin,
                
                You can check the status later using this command again
            '''
            with open(self.register_path, 'w') as json_file:
                json.dump([
                    *self.registerlist, {
                        'id': user.id,
                        'username': user.username,
                        'full_name': f'{user.first_name} {user.last_name}',
                    }
                ], json_file)

            logger.info('A new user requested registration!')

        if user.id in register_ids:
            response_string = 'You already registered yourself, please wait until an admin handles the request.'

        if user.id in self.whitelist:
            response_string = 'Your registration has been successful! You can now start using the bot.'

        if user.id in self.blacklist:
            response_string = 'Sorry, your request has been denied by an admin, you may stop using the bot.'

        update.message.reply_text(dedent(response_string))

    def audio(self, update: Update, _: CallbackContext):
        if update.effective_user.id not in self.whitelist:
            update.message.reply_text('You\'re not allowed to use the bot (yet).')
            return None

        if update.message.voice:
            file = update.message.voice.get_file()
        if update.message.audio:
            file = update.message.audio.get_file()

        threading.Thread(target=self.process_audio, args=[file, update]).start()

        response_string = f'''
                Message has been received!
                Please wait while the gibberish is being translated to text. ^^
                Depending on the length, this may take a while...
                
                Please remember, accuracy may vary.
            '''
        update.message.reply_text(dedent(response_string))

    def process_audio(self, file, update):
        full_file_path = os.path.join(self.file_path, file.file_unique_id)
        file.download(custom_path=full_file_path)
        audio = AudioSegment.from_file(full_file_path).set_frame_rate(16000).set_channels(1).set_sample_width(2)
        # TODO there must be a way to do this in memory directly
        wav_path = f'{full_file_path}.wav'
        audio.export(wav_path, format='wav')
        with open(wav_path, 'rb') as wav_file:
            wav_bytes = wav_file.read()
            response = requests.post(
                self.stt_address,
                data=wav_bytes,
            )
            os.remove(full_file_path)
            os.remove(wav_path)
            if not response.status_code == 200:
                response_message = 'Whoops! Something went wrong on my end. Please try again later.'
                if self.admin_name:
                    response_message = f'''
                    {response_message}\nif this keeps happening, you may wanna ask {self.admin_name} for help.
                    '''

                update.message.reply_text(dedent(response_message))
                return None

            decoded_message = bytes.decode(response.content, 'utf-8')
            update.message.reply_text(f'Okay, apparently the message said: {decoded_message}')

    @staticmethod
    def read_json(filepath):
        try:
            with open(filepath, 'r') as json_file:
                return json.load(json_file)
        except FileNotFoundError:
            logger.warning(f'{filepath} not found, creating it...')
            with open(filepath, 'w') as json_file:
                if 'register.json' in filepath:
                    json.dump([{}], json_file)
                else:
                    json.dump([], json_file)
                return []


telegramstt = TelegramSTT()
