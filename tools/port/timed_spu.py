"""Original DVD SPU PES timestamps and display-state intervals, offline only."""
from spu import decode_rle

def _pts(data):
    if len(data)!=5 or not all(data[i]&1 for i in [0,2,4]):raise ValueError('Invalid SPU PTS')
    return ((data[0]>>1&7)<<30)|(data[1]<<22)|((data[2]>>1)<<15)|(data[3]<<7)|(data[4]>>1)

def extract_timed_packets(data):
    buffers={};result=[]
    for start in range(0,len(data),2048):
        sector=data[start:start+2048]
        if len(sector)!=2048 or sector[:4]!=b'\0\0\1\xba':continue
        offset=14+(sector[13]&7)
        while offset+9<=len(sector) and sector[offset:offset+3]==b'\0\0\1':
            size=int.from_bytes(sector[offset+4:offset+6],'big');end=offset+6+size
            if not size or end>2048:break
            if sector[offset+3]==0xbd:
                payload=offset+9+sector[offset+8]
                if payload<end and 32<=sector[payload]<=63:
                    stream=sector[payload];buffer=buffers.get(stream)
                    if buffer is None:
                        if not sector[offset+7]&0x80 or sector[offset+8]<5:raise ValueError('SPU start has no PTS')
                        buffer={'pts':_pts(sector[offset+9:offset+14]),'sector':start//2048,'data':bytearray()};buffers[stream]=buffer
                    buffer['data'].extend(sector[payload+1:end])
                    while len(buffer['data'])>=4:
                        length=int.from_bytes(buffer['data'][:2],'big')
                        if length<4:raise ValueError('Invalid timed SPU length')
                        if len(buffer['data'])<length:break
                        result.append({'stream':stream,'pts':buffer['pts'],'sector':buffer['sector'],'data':bytes(buffer['data'][:length])})
                        del buffer['data'][:length]
                    if not buffer['data']:del buffers[stream]
            offset=end
    if any(b['data'] for b in buffers.values()):raise ValueError('Truncated timed SPU packet')
    return result

def display_intervals(packet):
    if len(packet)<4 or int.from_bytes(packet[:2],'big')!=len(packet):raise ValueError('Invalid SPU length')
    offset=int.from_bytes(packet[2:4],'big');seen=set();states=[]
    rect=None;fields=None;palette=alpha=0;visible=False
    while offset not in seen:
        seen.add(offset)
        if offset+4>len(packet):raise ValueError('Invalid SPU sequence')
        date=int.from_bytes(packet[offset:offset+2],'big')*1024
        next_offset=int.from_bytes(packet[offset+2:offset+4],'big');cursor=offset+4
        while cursor<len(packet):
            command=packet[cursor];cursor+=1
            if command==255:break
            sizes={0:0,1:0,2:0,3:2,4:2,5:6,6:4}
            if command not in sizes:raise ValueError(f'Unsupported timed SPU command {command:#x}')
            size=sizes[command];body=packet[cursor:cursor+size]
            if len(body)!=size:raise ValueError('Truncated SPU display command')
            cursor+=size
            if command in [0,1]:visible=True
            elif command==2:visible=False
            elif command==3:palette=int.from_bytes(body,'big')
            elif command==4:alpha=int.from_bytes(body,'big')
            elif command==5:
                x=(body[0]<<4)|(body[1]>>4);right=((body[1]&15)<<8)|body[2]
                y=(body[3]<<4)|(body[4]>>4);bottom=((body[4]&15)<<8)|body[5]
                rect={'x':x,'y':y,'width':right-x+1,'height':bottom-y+1}
            elif command==6:fields=(int.from_bytes(body[:2],'big'),int.from_bytes(body[2:],'big'))
        else:raise ValueError('Unterminated SPU display sequence')
        if states and date<states[-1]['startTicks']:raise ValueError('Unordered SPU display dates')
        states.append({'startTicks':date,'visible':visible,'rect':rect,'fields':fields,'palette':palette,'alpha':alpha})
        offset=next_offset
    result=[]
    for i,state in enumerate(states):
        end=states[i+1]['startTicks'] if i+1<len(states) else None
        if not state['visible'] or end==state['startTicks']:continue
        if state['rect'] is None or state['fields'] is None:raise ValueError('Visible SPU has no bitmap')
        pixels=decode_rle(packet,state['rect']['width'],state['rect']['height'],state['fields'])
        result.append({k:state[k] for k in ['startTicks','rect','palette','alpha']}|{'endTicks':end,'pixels':pixels})
    return result
