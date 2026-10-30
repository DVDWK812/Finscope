"""Exercise the shipped component's resize protocol with an offline parent."""
from pathlib import Path
import shutil
import subprocess
import unittest


class ChartProtocolTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js is needed for the component protocol check')
    def test_late_host_registration_recovers_without_infinite_ready_or_resize_messages(self):
        script=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(process.argv[1],'utf8').split('<script>')[1].split('</script>')[0];
let receive,ready=0,rendered=0;const timers=[],messages=[];
const element=()=>({style:{},setAttribute(){},append(){},replaceChildren(){rendered++},querySelectorAll(){return []},classList:{remove(){},add(){}}});
const root=element();root.getBoundingClientRect=()=>({height:200});
const document={getElementById:()=>root,createElement:element,createElementNS:element};
const parent={postMessage(m){messages.push(m);if(m.type==='streamlit:componentReady'&&++ready===2)
 receive({source:parent,data:{type:'streamlit:render',args:{kind:'cloud',scope:'authored',data:{terms:[]}}}});}};
vm.runInNewContext(source,{document,parent,addEventListener:(_,fn)=>receive=fn,ResizeObserver:class{observe(){}},
 setTimeout:fn=>timers.push(fn),Date});
let steps=0;while(timers.length&&steps++<20)timers.shift()();
assert.equal(rendered,1,'a dropped initial ready message must not leave the cloud blank');
assert.equal(ready,2);assert.equal(timers.length,0,'readiness retries must stop once rendered');
assert.equal(messages.filter(m=>m.type==='streamlit:setFrameHeight').length,1);
"""
        component=Path(__file__).resolve().parents[1]/'finscope/chart_component/index.html'
        result=subprocess.run([shutil.which('node'),'-e',script,str(component)],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
    @unittest.skipUnless(shutil.which('node'), 'Node.js is needed for the component protocol check')
    def test_parent_render_feedback_settles_and_real_height_changes_are_reported(self):
        # Simulate a host that rerenders after setFrameHeight. A same-size render
        # must settle, or replacing SVG nodes can swallow pointer/focus events.
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(process.argv[1],'utf8'),source=html.split('<script>')[1].split('</script>')[0];
let renders=0,observer,receive,rootHeight=500;const queue=[],messages=[];
const element=()=>({style:{},setAttribute(){},append(){},replaceChildren(){renders++},
  querySelectorAll(){return []},classList:{remove(){},add(){}}});
const root=element();root.getBoundingClientRect=()=>({height:rootHeight});
const document={getElementById:()=>root,createElement:element,createElementNS:element,
  documentElement:{scrollHeight:500}};
const render=()=>receive({source:parent,data:{type:'streamlit:render',args:{kind:'graph',scope:'authored',data:{nodes:[],edges:[]}}}});
const parent={postMessage(message){messages.push(message);if(message.type==='streamlit:setFrameHeight'){
  // The viewport/document may include host padding or injected diagnostics;
  // it is not a measurement of the component's own content.
  document.documentElement.scrollHeight=message.height+30;
  queue.push(render,()=>observer());}}};
vm.runInNewContext(source,{document,parent,addEventListener:(_,fn)=>receive=fn,
  ResizeObserver:class{constructor(fn){observer=fn}observe(){}},setTimeout:()=>0,Date});
render();let steps=0;while(queue.length&&steps++<20)queue.shift()();
assert.equal(queue.length,0,'same-height frame/render feedback must settle');
assert.equal(messages.filter(m=>m.type==='streamlit:setFrameHeight').length,1);
for(let i=0;i<100;i++)observer();
assert.equal(messages.filter(m=>m.type==='streamlit:setFrameHeight').length,1);
rootHeight=650;observer();
while(queue.length&&steps++<40)queue.shift()();
assert.equal(queue.length,0);assert.deepEqual(messages.filter(m=>m.type==='streamlit:setFrameHeight').map(m=>m.height),[500,650]);
console.log('component protocol settled; real height changes retained');
"""
        component = Path(__file__).resolve().parents[1] / 'finscope/chart_component/index.html'
        result = subprocess.run([shutil.which('node'), '-e', script, str(component)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
