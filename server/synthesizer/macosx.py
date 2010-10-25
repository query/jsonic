'''
Mac OS X speech synthesizer implementation for JSonic using `say`.

:requires: Python 2.6, iterpipes 0.3, Mac OS X 10.6
:copyright: Roger Que 2010
:license: BSD
'''
from synthesizer import *

from AppKit import NSSpeechSynthesizer
import hashlib
import iterpipes
import os.path

class MacOSXSpeechSynth(ISynthesizer):
    '''
    Synthesizes speech using the Mac OS X `say` command (10.6 or later).
    
    :ivar _path: Output cache path
    :ivar _opts: Command line options for `say`
    :cvar INFO: Dictionary of all supported engine properties cached for 
        fast responses to queries
    '''
    INFO = None
    
    def __init__(self, path, properties):
        '''Implements ISynthesizer constructor.'''
        # path where to write the file
        self._path = path
        # NSSpeechSynthesizer options for this synth instance
        self._opts = []
        
        try:
            voice = str(properties['voice'])
            assert voice in MacOSXSpeechSynth.get_info()['voices']['values']
            self._opts.append(voice)
        except AssertionError:
            raise SynthesizerError('invalid voice')
        except KeyError:
            self._opts.append('Alex')

        # store property portion of filename
        self._optHash = hashlib.sha1('macosx' + str(self._opts)).hexdigest()

    def write_wav(self, utterance):
        '''Implements ISynthesizer.write_wav.'''
        utf8Utterance = utterance.encode('utf-8')
        utterHash = hashlib.sha1(utf8Utterance).hexdigest()
        hashFn = '%s-%s' % (utterHash, self._optHash)
        # write wave file into path
        wav = os.path.join(self._path, hashFn+'.wav')
        if not os.path.isfile(wav):
            args = self._opts + [wav]
            c = iterpipes.cmd('say --file-format=WAVE --data-format=LEI16 -v {} -o {}', *args, encoding='utf-8')
            ret = iterpipes.call(c, utterance)
        return hashFn

    @classmethod
    def get_info(cls):
        '''Implements ISynthesizer.get_info.'''
        if cls.INFO is None:
            voices = NSSpeechSynthesizer.availableVoices()
            cls.INFO = {
                'voices' : {
                    'values' : [x.split('.')[-1] for x in voices],
                    'default' : 'Alex'
                }
            }
        return cls.INFO

SynthClass = MacOSXSpeechSynth

# Make sure that `say` is available.
iterpipes.check_call(iterpipes.linecmd('say ""'))