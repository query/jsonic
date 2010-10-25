'''
Speech synthesizer implementations for JSonic.

:var IMPLEMENTED_SYNTHS: Names of modules containing ISynthesizer
    implementations
:type IMPLEMENTED_SYNTHS: list
:var AVAILABLE_SYNTHS: Names paired with ISynthesizer implementations that
    are available to this instance of JSonic
:type AVAILABLE_SYNTHS: dict

:requires: Python 2.6
:copyright: Peter Parente 2010, Roger Que 2010
:license: BSD
'''
import imp
import linecache
import logging
import os.path
import sys

class SynthesizerError(Exception): 
    '''
    Exception to throw for any synthesis error, including a human readable
    description of what went wrong.
    '''
    pass

class ISynthesizer(object):
    '''
    All synthesizers must implement this instance and class interface.
    '''
    def __init__(self, path, properties):
        '''
        Constructor.
        
        :param path: Path to where synthesized files are stored
        :type path: str
        :param properties: Speech properties for any synthesis performed using
            this instance of the synthesizer. The supported properties are 
            dictated by the synthesizer implementation as returned by the
            get_info class method.
        :param properties: dict 
        '''
        raise NotImplementedError
    
    def write_wav(self, utterance):
        '''
        Synthesizes an utterance to a WAV file on disk in the cache folder. 
        The name of the file must be in the following format:

        <sha1 hash of utterance>-<sha1 hash of engine + synth properties>.wav
        
        :param utterance: Unicode text to synthesize as speech
        :type utterance: unicode
        :return: Root name of the WAV file on disk, sans extension
        :rtype: str
        '''
        raise NotImplementedError
    
    @classmethod
    def get_info(cls):
        '''
        Gets information about the speech properties supported by this 
        synthesizer. Caches this information whenever possible to speed future
        queries.
        
        :return: A dictionary describing the properties supported by this
            synthesizer. The common properties are defined as follows:
            
            {
                'rate' : { // always in words per minute
                    'minimum' : <number>,
                    'maximum' : <number>,
                    'default' : <number>
                },
                'pitch' : {
                    'minimum' : <number>,
                    'maximum' : <number>,
                    'default' : <number>
                },
                'voices' : {
                    'values' : [<str>, <str>, ...],
                    'default' : <str>
                }
            }
            
            If any of these properties are not supported, they should be left
            out of the dictionary. If additional properties are supported they 
            can be included in dictionary in a similar format.
        :rtype: dict
        :raises: RuntimeError if the engine is not available on the server
        '''
        raise NotImplementedError

# A dictionary containing the names of modules containing synth implementations
# provided by JSonic, mapped to a boolean value indicating whether support for
# this module is required.  For example, the espeak module is used as a default
# synthesizer module in other parts of JSonic, so an exception should be thrown
# if it is not successfully imported.
IMPLEMENTED_SYNTHS = { 'espeak': True, 'macosx': False }

# Populate the SYNTHS dictionary with synthesizer implementations that are
# available to JSonic.  Synthesizer modules that are successfully imported are
# assumed to function properly; prerequisites can be checked in the main body
# of a module (outside classes and functions) and exceptions raised to prevent
# synthesizers from being added to SYNTHS on platforms where they do not work.
AVAILABLE_SYNTHS = {}

# Look for synth modules in these directories.
synth_path = [os.path.dirname(__file__)]

# init() would ordinarily be module-level code, but since it performs logging
# of successful and unsuccessful module imports, it must be called after the
# run() method in jsonic.py has initialized the logging module.
def init():
    '''
    Populates JSonic's dictionary of available synthesizer classes.
    '''
    for synth in IMPLEMENTED_SYNTHS:
        module_info = imp.find_module(synth, synth_path)
        try:
            module = imp.load_module(synth, *module_info)
            synth_class = module.SynthClass
        except:
            sys.modules.pop(synth, None)
            logging.info('Could not import synth module "%s"', synth, exc_info=True)
            if IMPLEMENTED_SYNTHS[synth]:
                raise SynthesizerError('Required synth module "%s" is unavailable' % synth)
        else:
            AVAILABLE_SYNTHS[synth] = synth_class
            logging.info('Successfully imported synth module "%s"', synth)
        
    linecache.checkcache()

def get_class(name):
    '''
    Gets the synthesizer class associated with the given synth engine name.
    
    :param name: Name of the synthesizer
    :type name: str
    :return: ISynthesizer class or None if the name is unknown
    :rtype: cls
    '''
    return AVAILABLE_SYNTHS.get(name, None)