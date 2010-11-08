'''
Mac OS X speech synthesizer implementation for JSonic using PyObjC.

:requires: Python 2.6, Mac OS X 10.6
:copyright: Roger Que 2010
:license: BSD
'''
from synthesizer import *

import AppKit
from PyObjCTools.AppHelper import installMachInterrupt
import QTKit

import hashlib
import os.path
import struct
import subprocess
import sys

class MacOSXSpeechSynth(ISynthesizer):
    '''
    Synthesizes speech using NSSpeechSynthesizer (Mac OS X 10.6 or later).
    
    :ivar _path: Output cache path
    :ivar _opts: NSSpeechSynthesizer options list
    :cvar MIN_RATE: Minimum rate supported in WPM
    :cvar MAX_RATE: Maximum rate supported in WPM
    :cvar INFO: Dictionary of all supported engine properties cached for 
        fast responses to queries
    '''
    MIN_RATE = 80
    MAX_RATE = 390
    INFO = None
    
    def __init__(self, path, properties):
        '''Implements ISynthesizer constructor.'''
        # path where to write the file
        self._path = path
        # NSSpeechSynthesizer options for this synth instance
        self._opts = []
        
        try:
            rate = int(properties['rate'])
            rate = min(max(rate, self.MIN_RATE), self.MAX_RATE)
            self._opts.append(str(rate))
        except TypeError:
            raise SynthesizerError('invalid rate')
        except KeyError:
            self._opts.append('200')
        
        try:
            voice = str(properties['voice'])
            assert voice in MacOSXSpeechSynth.get_info()['voices']['values']
            self._opts.append(voice)
        except AssertionError:
            raise SynthesizerError('invalid voice')
        except KeyError:
            self._opts.append('default')

        # store property portion of filename
        self._optHash = hashlib.sha1('macosx' + str(self._opts)).hexdigest()

    def write_wav(self, utterance):
        '''Implements ISynthesizer.write_wav.'''
        utf8Utterance = utterance.encode('utf-8')
        utterHash = hashlib.sha1(utf8Utterance).hexdigest()
        hashFn = '%s-%s' % (utterHash, self._optHash)
        
        # Invoke the __main__ portion of this file on the command line, passing 
        # in the rate, voice, and output prefix name as arguments, and the text 
        # to utter on standard input.
        prefix = os.path.join(self._path, hashFn)
        if not os.path.isfile(prefix + '.wav'):
            args = [sys.executable, __file__] + self._opts + [os.path.abspath(prefix)]
            p = subprocess.Popen(args, stdin=subprocess.PIPE,
                                 env={'PYTHONPATH': '.'})
            p.communicate(utterance)
        return hashFn

    @classmethod
    def get_info(cls):
        '''Implements ISynthesizer.get_info.'''
        if cls.INFO is None:
            voices = AppKit.NSSpeechSynthesizer.availableVoices()
            cls.INFO = {
                'rate' : {
                    'minimum' : cls.MIN_RATE, 
                    'maximum' : cls.MAX_RATE,
                    'default' : 200
                },
                'voices' : {
                    'values' : list(voices) + ['default'],
                    'default' : 'default'
                }
            }
        return cls.INFO

SynthClass = MacOSXSpeechSynth

# Setting up NSApplication delegates requires that Cocoa code be executed in a 
# separate process.  This module invokes itself in MacOSXSpeechSynth.write_wav.
if __name__ == '__main__':
    rate = float(sys.argv[1])
    voice = sys.argv[2]
    if voice == 'default':
        voice = None
    prefix = sys.argv[3]
    utterance = sys.stdin.read().decode('utf-8')
    
    aiff_url = 'file://' + prefix + '.aiff'
    wav_file = prefix + '.wav'
    
    def long_from_string(s):
        '''
        Unpacks a human-readable QuickTime file type code to an NSNumber used 
        internally by QTKit.
        '''
        return AppKit.NSNumber.numberWithLong_(struct.unpack('>l', s)[0])
    
    class MacOSXSynthError(SynthesizerError):
        '''
        Wrapper for NSError instances thrown during the speech synthesis and 
        file conversion process.
        '''
        
        @classmethod
        def from_nserror(cls, nserror):
            return cls(nserror.userInfo()['NSLocalizedDescription'])
    
    class SynthDelegate(AppKit.NSObject):
        '''
        NSApplication delegate for initiating speech synthesis and converting 
        the AIFF output of NSSpeechSynthesizer to WAV through QTKit.
        '''
        
        def applicationDidFinishLaunching_(self, app):
            '''Called when the NSApplication has finished initialization.'''
            speech = AppKit.NSSpeechSynthesizer.alloc().init()
            speech.setDelegate_(self)
            
            # Setting the voice resets the speaking rate, so the former must be 
            # set before the latter.
            speech.setVoice_(voice)
            speech.setRate_(rate)
            
            speech.startSpeakingString_toURL_(utterance,
                                              AppKit.NSURL.URLWithString_(aiff_url))
        
        def speechSynthesizer_didFinishSpeaking_(self, synth, finishedSpeaking):
            '''Called when a speech synthesis operation has finished.'''
            
            # finishedSpeaking is supposed to indicate whether speech was 
            # synthesized successfully; however, it is False even in many cases 
            # when speech synthesis has encountered no visible issues, so this 
            # function ignores its value.
            
            movie, error = QTKit.QTMovie.movieWithURL_error_(
                AppKit.NSURL.URLWithString_(aiff_url), None)

            if movie is None:
                raise MacOSXSynthError.from_nserror(error)

            out_attrs = {
                'QTMovieExport': True,
                'QTMovieExportType': long_from_string('WAVE')
            }
            status, error = movie.writeToFile_withAttributes_error_(
                wav_file, out_attrs, None)
            
            if not status:
                raise MacOSXSynthError.from_nserror(error)

            # Clean up after ourselves by removing the original AIFF file.
            os.remove(prefix + '.aiff')

            AppKit.NSApp().terminate_(self)

    app = AppKit.NSApplication.sharedApplication()
    delegate = SynthDelegate.alloc().init()
    app.setDelegate_(delegate)
    installMachInterrupt()
    app.run()
