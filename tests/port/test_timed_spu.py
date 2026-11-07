import json,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/port'))

def packet():
    #2x2 bitmap, white/opaque at0; alpha changes at45; display stops at90.
    body=bytes.fromhex('90900000')
    first=bytes.fromhex('00000020 01 030010 0400f0 05000001000001 0600040005 ff')
    second=bytes.fromhex('002d0028 040080 ff')
    stop=bytes.fromhex('005a0028 02 ff')
    data=body+first+second+stop
    return (len(data)+4).to_bytes(2,'big')+b'\x00\x08'+data

class TimedSpuTests(unittest.TestCase):
    def test_display_dates_colour_and_alpha_changes_are_retained(self):
        from timed_spu import display_intervals
        events=display_intervals(packet())
        self.assertEqual([(e['startTicks'],e['endTicks'],e['palette'],e['alpha']) for e in events],[(0,46080,16,240),(46080,92160,16,128)])
        self.assertEqual(events[0]['rect'],{'x':0,'y':0,'width':2,'height':2})
        self.assertEqual(events[0]['pixels'],[[1,1],[1,1]])

    def test_fragmented_spu_keeps_its_initial_pes_timestamp(self):
        from timed_spu import extract_timed_packets
        pts=180000000
        stamp=bytes([0x21|((pts>>30&7)<<1),(pts>>22)&255,((pts>>15&127)<<1)|1,(pts>>7)&255,((pts&127)<<1)|1])
        def sector(fragment,first):
            header=b'\x80\x80\x05'+stamp if first else b'\x80\x00\x00'
            pes=header+b'\x20'+fragment
            value=b'\0\0\1\xba'+bytes(10)+b'\0\0\1\xbd'+len(pes).to_bytes(2,'big')+pes
            return value+bytes([255])*(2048-len(value))
        p=packet();actual=extract_timed_packets(sector(p[:20],True)+sector(p[20:],False))
        self.assertEqual([(r['stream'],r['pts'],r['sector'],r['data']) for r in actual],[(32,pts,0,p)])

    def test_original_instruction_subtitle_pts_match_independent_ffprobe(self):
        from timed_spu import extract_timed_packets,display_intervals
        from extras_source import ExtrasSource
        from export_round import Assets
        with ExtrasSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            a=Assets(ROOT/'disc/2EDVD108',ROOT/'analysis',ROOT/'app/public',m.pgcs)
            path,raw=a.raw({'vts':2,'domain':'title','pgc':1,'cell':1,'audio':0})
            packets=[p for p in extract_timed_packets(raw) if p['stream']==32]
            probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','s:0','-show_packets','-show_entries','packet=pts','-of','json',str(path)]))
            self.assertEqual([p['pts'] for p in packets],[int(p['pts']) for p in probe['packets']])
            self.assertGreater(len(packets),10)
            for p in packets:
                intervals=display_intervals(p['data']);self.assertTrue(intervals)
                self.assertTrue(all(e['endTicks'] is not None and e['endTicks']>e['startTicks'] for e in intervals))
