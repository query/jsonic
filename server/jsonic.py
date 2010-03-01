'''
Speech server implementation for JSonic using Tornado web server and Mongo 
database.

:requires: Python 2.6, Tornado 0.2, PyMongo 1.4
:copyright: Peter Parente 2010
:license: BSD
'''
import synthesizer
import encoder
import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.escape import json_encode, json_decode
import pymongo
import multiprocessing
import email.utils
import mimetypes
import datetime
import time
import os
import stat

# path containing synthed and encoded speech files
CACHE_PATH = os.path.join(os.path.dirname(__file__), 'files')
try:
    os.mkdir(CACHE_PATH)
except OSError:
    pass

def synthesize(engineCls, encoderCls, utterances, properties):
    '''
    Executes speech synthesis and encoding in a separate process in the worker 
    pool to avoid blocking the Tornado server.
    
    :param engineCls: ISynthesizer implementation to use for synth
    :type engineCls: class
    :param encoderCls: IEncoder implementation to use for encoding
    :type encoderCls: class
    :param utterances: Dictionary of utterance IDs (keys) paired with unicode
        utterance strings to synthesize (values)
    :type utterances: dict
    :param properties: Dictionary of properties to use when synthesizing. 
        The properties supported are determined by the engineCls implementation
        of ISynthesizer.get_info.
    :type properties: dict
    :return: A dictionary describing the results of worker in the following
        format on success:
        
        {
            'success' : True,
            'result' : {
                'id1' : 'utterance filname1',
                'id2' : 'utterance filname2',
                ...
            }
        }
        
        where the IDs matches those paired with the text utterances passed
        to the function.
        
        On error, the result is in the following format:
        
        {
            'success' : False,
            'description' : <str>
        }
        
        where the description is a developer-readable explanation of why
        synthesis failed.
    :rtype: dict
    '''
    response = {'success' : False}
    try:
        engine = engineCls(CACHE_PATH, properties)
    except synthesizer.SynthesizerError, e:
        response['description'] = str(e)
        return response
    try:
        enc = encoderCls(CACHE_PATH)
    except encoder.EncoderError, e:
        response['description'] = str(e)
        return response
    response['success'] = True
    response['result'] = {}
    for key, text in utterances.items():
        hashFn = engine.write_wav(text)
        enc.encode_wav(hashFn)
        response['result'][key] = hashFn
    return response

class JSonicHandler(tornado.web.RequestHandler):
    '''
    Base class for all handlers.
    '''
    def send_json_error(self, response):
        '''
        Sends a HTTP 500 error with a JSON body containing more information
        about the error. Finishes the HTTP response to prevent further output.
        
        :param response: Response from a handler implementation to be 
            serialized as JSON. Contains at least a boolean `success` field 
            that is alway set to false to indicate an error.
        :type response: dict
        '''
        self.clear()
        self.set_status(500)
        #self.set_header('Content-Type', 'application/json')
        response['success'] = False
        message = self.write(response)
        self.finish(message)

class SynthHandler(JSonicHandler):
    '''
    Synthesizes speech to an encoded file for a later fetch from a static file 
    URL.
    '''
    @tornado.web.asynchronous
    def post(self):
        '''
        Performs speech synthesis of the utterances posted in the following
        JSON format:
        
        {
            "format" : <unicode>,
            "utterances" : {
                "id1" : <unicode>,
                "id2" : <unicode>,
                ...
            },
            "properties" : {
                "property1" : <any>,
                "property2" : <any>,
                ...
            }
        }
        
        where the format dicates the encoding for the resulting speech files,
        the utterance values are the text to synthesize as speech,
        and the property names and values are those supported by the selected
        engine (also one of the properties).
        
        Responds with information about the synthesized utterances in the
        following JSON format on success:
        
        {
            "success" : true,
            "result" : {
                "id1" : <unicode>,
                "id2"" : <unicode>,
                ...
            }
        }
        
        where the utterance keys match those in the request and the values are 
        the filenames of the synthesized files accessible using the 
        FilesHandler. 

        Responds with the following JSON error if synthesis fails:
        
        {
            "success" : false,
            "description" : <unicode>
        }
        '''
        args = json_decode(self.request.body)
        pool = self.application.settings['pool']
        engine = synthesizer.get_class(args.get('engine', 'espeak'))
        if engine is None:
            self.send_json_error({'description' : 'unknown speech engine'})
            return
        enc = encoder.get_class(args.get('format', '.ogg'))
        if enc is None:
            self.send_json_error({'description' : 'unknown encoder format'})
            return
        params = (engine, enc, args['utterances'], args['properties'])
        pool.apply_async(synthesize, params, callback=self.on_synth_complete)
        #self.on_synth_complete(synthesize(*params))
    
    def on_synth_complete(self, response):
        if response['success']:
            #self.set_header('Content-Type', 'application/json')
            self.write(response)
            self.finish()
        else:
            self.send_json_error(response)

class EngineHandler(JSonicHandler):
    '''
    Retrieves information about available speech synthesis engines.
    '''
    def get(self, name=None):
        '''
        Responds with a list of all engines if name is None in the following 
        JSON format:
        
        {
            "success" : true,
            "result" : [<unicode>, <unicode>, ...]
        }

        Responds with the properties supported by a single engine in the 
        following JSON format if name is a valid engine name. The exact fields 
        available are dependent on the ISynthesizer.get_info implementation for
        the engine.
        
        {
            "success" : true,
            "result" {
                "range_property" {
                    "minimum" : <number>,
                    "maximum" : <number>,
                    "default" : <number>
                },
                "enumeration_property" : {
                    "values" : [<unicode>, <unicode>, ...],
                    "default" : <unicode>
                },
                ...
            }
        }
        
        Responds with the following JSON error if information about the named
        engine is unavailable:
        
        {
            "success" : false,
            "description" : <unicode>
        }
        
        :param name: Name of the engine to query for details or None to get
            a list of all supported engines. Defaults to None.
        :param name: str
        '''
        if name is None:
            names = synthesizer.SYNTHS.keys()
            ret = {'success' : True, 'result' : names}
            self.write(json_encode(ret))
        else:
            cls = synthesizer.get_class(name)
            if cls is None:
                self.send_json_error({'description' : 'invalid engine'})
            else:
                info = cls.get_info()
                ret = {'success' : True, 'result' : info}
                self.write(ret)

# @todo: implement using mongo + worker pool for 
class CacheHandler(JSonicHandler):
    '''
    Stores and retrieves utterance caching metrics on behalf of an application.
    Used by an application to warm its client-side cache at load time to 
    reduce speech and sound output latency.
    '''
    def get(self, app):
        pass
    
    def post(self, app):
        pass

class FilesHandler(tornado.web.StaticFileHandler):
    '''
    Retrieves cached speech files. Overrides the base class implementation to
    support partial content requests. 
    
    This handler should not be used if your deployment places the Tornado
    web server behind a proxy such as nginx which is much better at serving
    up static files. It is provided to make JSonic an all-in-one package if
    so desired.
    '''
    def get(self, path, include_body=True):
        '''
        Gets bytes from a synthesized, encoded speech file.
        
        :param path: Path to the file
        :type path: str
        :param include_body: Include the body of the file if modified?
        :type include_body: bool
        '''
        abspath = os.path.abspath(os.path.join(self.root, path))
        if not abspath.startswith(self.root):
            raise HTTPError(403, "%s is not in root static directory", path)
        if not os.path.exists(abspath):
            raise HTTPError(404)
        if not os.path.isfile(abspath):
            raise HTTPError(403, "%s is not a file", path)
 
        stat_result = os.stat(abspath)
        modified = datetime.datetime.fromtimestamp(stat_result[stat.ST_MTIME])
 
        self.set_header("Last-Modified", modified)
        if "v" in self.request.arguments:
            self.set_header("Expires", datetime.datetime.utcnow() + \
                                       datetime.timedelta(days=365*10))
            self.set_header("Cache-Control", "max-age=" + str(86400*365*10))
        else:
            self.set_header("Cache-Control", "public")
        mime_type, encoding = mimetypes.guess_type(abspath)
        if mime_type:
            self.set_header("Content-Type", mime_type)
 
        # Check the If-Modified-Since, and don't send the result if the
        # content has not been modified
        ims_value = self.request.headers.get("If-Modified-Since")
        if ims_value is not None:
            date_tuple = email.utils.parsedate(ims_value)
            if_since = datetime.datetime.fromtimestamp(time.mktime(date_tuple))
            if if_since >= modified:
                self.set_status(304)
                return
 
        if not include_body:
            return
        
        # check if there's a range request
        rng = self.request.headers.get('Range')
        if rng is None:
            # send the whole file
            start = 0
            size = stat_result[stat.ST_SIZE]
            self.set_header("Content-Length", str(size))
        else:
            self.set_status(206)
            # send just the requested bytes
            kind, rng = rng.split('=')
            start, end = rng.split('-')
            if not end: end = stat_result[stat.ST_SIZE]-1
            start = int(start)
            end = int(end)
            size = end - start + 1
            self.set_header("Content-Length", str(size))
            self.set_header("Content-Range", 'bytes %d-%d/%d' %
                (start, end, stat_result[stat.ST_SIZE]))
            file = open(abspath, "rb")
        try:
            file.seek(start)
            self.write(file.read(size))
        finally:
            file.close()

def run_server(processes=4, debug=False):
    '''
    Runs an instance of the JSonic server.
    
    :param debug: True to enable automatic server reloading for debugging.
        Defaults to False.
    :type debug: bool
    :param processes: Number of worker processes for synthesis and caching
        operations. Defaults to 4.
    :type processes: int
    '''
    kwargs = {}
    kwargs['pool'] = pool = multiprocessing.Pool(processes=processes)
    if debug:
        # serve static files for debugging purposes
        kwargs['static_path'] = os.path.join(os.path.dirname(__file__), "../")
    application = tornado.web.Application([
        (r'/engine', EngineHandler),
        (r'/engine/([a-zA-Z0-9]+)', EngineHandler),
        (r'/synth', SynthHandler),
        (r'/files/([a-f0-9]+-[a-f0-9]+\..*)', FilesHandler, {'path' : './files'}),
        (r'/cache/([a-z0-9]+)', CacheHandler)
    ], debug=debug, **kwargs)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)
    ioloop = tornado.ioloop.IOLoop.instance()
    ioloop.start()

if __name__ == '__main__':
    run_server(processes=4, debug=True)