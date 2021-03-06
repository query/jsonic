dojo.provide('uow.audio.tests.sequential');

(function() {
    var mods = [
        {n : 'sequential', args : {defaultCaching : false}},
        {n : 'sequential+cache', args : {defaultCaching : true}}
    ];
    dojo.forEach(mods, function(mod) {
        module(mod.n, getModOpts(mod.args));
        test('say 1 then say 1 again', 4, function() {
            stop(TO*2);
            var before = 0;
            var after = 0;
            var def1 = this.js.say({text : UT1});
            var def2 = this.js.say({text : UT1});
            def1.callBefore(function() {
                ok(before === 0, 'first utterance started first');
                before = 1;
            }).callAfter(function(completed) {
                ok(after === 0 && completed, 'first utterance finished first');
                after = 1;
            });
            def2.callBefore(function() {
                ok(before === 1, 'second utterance started second');
            }).callAfter(function(completed) {
                ok(after === 1 && completed, 'second utterance finished second');
                start();
            });
        });
        test('say 1 then say 2', 4, function() {
            stop(TO*2);
            var before = 0;
            var after = 0;
            var def1 = this.js.say({text : UT1});
            var def2 = this.js.say({text : UT2});
            def1.callBefore(function() {
                ok(before === 0, 'first utterance started first');
                before = 1;
            }).callAfter(function(completed) {
                ok(after === 0 && completed, 'first utterance finished first');
                after = 1;
            });
            def2.callBefore(function() {
                ok(before === 1, 'second utterance started second');
            }).callAfter(function(completed) {
                ok(after === 1 && completed, 'second utterance finished second');
                start();
            });
        });
        test('say then play', 4, function() {
            stop(TO*2);
            var before = 0;
            var after = 0;
            var def1 = this.js.say({text : UT1});
            var def2 = this.js.play({url : SND1});
            def1.callBefore(function() {
                ok(before === 0, 'utterance started first');
                before = 1;
            }).callAfter(function(completed) {
                ok(after === 0 && completed, 'utterance finished first');
                after = 1;
            });
            def2.callBefore(function() {
                ok(before === 1, 'sound started second');
            }).callAfter(function(completed) {
                ok(after === 1 && completed, 'sound finished second');
                start();
            });
        });
        test('play then say', 4, function() {
            stop(TO*2);
            var before = 0;
            var after = 0;
            var def1 = this.js.play({url : SND1});
            var def2 = this.js.say({text : UT1});
            def1.callBefore(function() {
                ok(before === 0, 'sound started first');
                before = 1;
            }).callAfter(function(completed) {
                ok(after === 0 && completed, 'sound finished first');
                after = 1;
            });
            def2.callBefore(function() {
                ok(before === 1, 'utterance started second');
            }).callAfter(function(completed) {
                ok(after === 1 && completed, 'utterance finished second');
                start();
            });
        });
        test('play 1 then play 1 again', 4, function() {
            stop(TO*2);
            var before = 0;
            var after = 0;
            var def1 = this.js.play({url : SND1});
            var def2 = this.js.play({url : SND1});
            def1.callBefore(function() {
                ok(before === 0, 'first sound started first');
                before = 1;
            }).callAfter(function(completed) {
                ok(after === 0 && completed, 'first sound finished first');
                after = 1;
            });
            def2.callBefore(function() {
                ok(before === 1, 'second sound started second');
            }).callAfter(function(completed) {
                ok(after === 1 && completed, 'second sound finished second');
                start();
            });
        });
        test('play 1 then play 2', 4, function() {
            stop(TO*2);
            var before = 0;
            var after = 0;
            var def1 = this.js.play({url : SND1});
            var def2 = this.js.play({url : SND2});
            def1.callBefore(function() {
                ok(before === 0, 'first sound started first');
                before = 1;
            }).callAfter(function(completed) {
                ok(after === 0 && completed, 'first sound finished first');
                after = 1;
            });
            def2.callBefore(function() {
                ok(before === 1, 'second sound started second');
            }).callAfter(function(completed) {
                ok(after === 1 && completed, 'second sound finished second');
                start();
            });
        });   
    });
})();