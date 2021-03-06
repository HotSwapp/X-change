from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import string,cgi,time, json, random, copy, cPickle, image64, os, copy
import pybitcointools as pt
try:
    from jsonrpc import ServiceProxy
except:
    try:
        from bitcoinrpc import AuthServiceProxy as ServiceProxy       
    except:
        from bitcoinrpc import authproxy as ServiceProxy#because bitcoinrpc renamed their object
#stuff that can be customized for each computer
users_db='users.db'
PORT=80

def currencies(currency):
    if currency=='bitcoin':
        return ServiceProxy("http://:xS7qmI7NpR@127.0.0.1:8332/")
    if currency=='litecoin':
        return ServiceProxy("http://HardToGuessUsername:HardToGuessPassword@127.0.0.1:9332/")
    else:
        print('currency {} is not yet installed'.format(currency))

#database junk
try:
    import gdbm
    def users_load(user):
        out=gdbm.open(users_db, 'c')
        if not out.has_key(user):
            users_save(user, {})
            out=gdbm.open(users_db, 'c')
        return json.loads(out[user])
    def users_save(user, db):
        string=json.dumps(db)
        out=gdbm.open(users_db, 'c')
        out[user]=string
        out.close()
except:
    def users_load(user):
        out=cPickle.load(open(users_db, 'rb'))
        return json.loads(out[user])
    def users_save(user, db):
        string=json.dumps(db)
        out=cPickle.load(open(users_db, 'rb'))
        out[user]=string
        cPickle.dump(out, open(users_db, 'wb'))

#currencies('bitcoin').move('', '04337ae95e50f7a0e73229c2e65193f50d46506fb074b185fdae6bf1f2b47c6489b1ed8455838eb9cc14ecbfc8902f63376a672daff64da145f2b40d51ebaab2ca', 0.0002)
def fs_load(database):
    try:
        out=cPickle.load(open(database, 'rb'))
        return out
    except:
        fs_save(database, [])#this are list-databases
        return cPickle.load(open(database, 'rb'))      

def fs_save(database, dic):
    cPickle.dump(dic, open(database, 'wb'))
def load_trades(trade):
    file=trade['buy_currency']+'_'+trade['sell_currency']+'_trades.db'
    out=[]
    with open(file, 'rb') as myfile:
        a=myfile.readlines()
        for i in a:
            if i.__contains__('"'):
                out.append(json.loads(i.strip('\n')))
    return out
def reset_trades(file):
    open(file, 'w').close()
def append_to_trades(trade):#to local pool
    file=trade['buy_currency']+'_'+trade['sell_currency']+'_trades.db'
    with open(file, 'a') as myfile:
        myfile.write(json.dumps(tx)+'\n')

def available_bids(buy_currency, buy_amount, sell_currency, sell_amount):
    file=buy_currency+'_'+sell_currency+'_bids.db'
    temp={'sell_amount':sell_amount, 'buy_amount':buy_amount}
    bids=fs_load(file)
    print('bids : ' +str(bids))
    out=filter(lambda x: price(x)>=price(temp), bids)
    return out
def price(bid):
    return float(bid['sell_amount'])/float(bid['buy_amount'])
def add2bids(newbid):#adds to users and bids
    def insert(a, l, f):
        beg=[]
        c=True
        print('a: ' +str(a))
        print('l: ' +str(l))
        while c:
            if l==[]:
                return beg+[a]
            if f(a)<f(l[0]):
                beg=beg+[l[0]]
                l=l[1:]
            else:
                return beg+[a]+l
    file=newbid['buy_currency']+'_'+newbid['sell_currency']+'_bids.db'
    bids=fs_load(file)
    for bid in bids:
        if bid['bid_id']==newbid['bid_id']:
            bids.remove(bid)
    bids=insert(newbid, bids, price)
    fs_save(file, bids)
    user=users_load(newbid['owner'])
    if 'bids' not in user:
        user['bids']=[]
    for bid in user['bids']:
        if bid['bid_id']==newbid['bid_id']:
            user['bids'].remove(bid)
    user['bids']=insert(newbid, user['bids'], price)
    users_save(newbid['owner'], user)
def remove_bid(bid):
    sell_currency=bid['sell_currency']
    buy_currency=bid['buy_currency']
    file=buy_currency+'_'+sell_currency+'_bids.db'
    user=users_load(bid['owner'])
    for i in user['bids']:
        if bid['bid_id']==i['bid_id']:
            user['bids'].remove(i)#remove from file
    users_save(bid['owner'], user)
    bids=fs_load(file)
    for i in bids:
        if bid['bid_id']==i['bid_id']:
            bids.remove(i)#remove from file
    fs_save(file, bids)
def adjust_bid(bid, percent):
    if percent>1.0 or percent<1.0:
        return package({'type':'error','message':'<p>percent should be between 0 and 1</p>'})
    part_bid=bid
    part_bid['buy_amount']=part_bid['buy_amount']*(1-p)
    part_bid['sell_amount']=part_bid['sell_amount']*(1-p)
    append_to_trades(part_bid)
    remove_bid(bid)
    newbid=bid
    newbid['buy_amount']=bid['buy_amount']*p
    newbid['sell_amount']=bid['sell_amount']*p
    add2bids(newbid)
def package(dic):
    return json.dumps(dic).encode('hex')
def unpackage(dic):
    return json.loads(dic.decode('hex'))

#core functionality
def execute_command(command):
    print('4')
    print(command)
    c=command['command']
    if c=='deposit_address':
        return deposit_address(command)
    elif c=='withdraw':
        return withdraw(command)
    elif c=='user_data':
        print('5')
        return user_data(command)
    elif c=='buy_bid':
        return buy_bid(command)
    elif c=='sell_bid':
        return sell_bid(command)
    else:
        return package({'type':'error','message':'poorly formatted command'})
def checkSig(dic):
    print('in func checksig')
    bad_password_page=empty_page.format('''
    The signature that you gave: {} <br />
    Does not match the command that you gave: {}{}''')
    command=dic['command']
    signature=unpackage(dic['signature'])
    dic=unpackage(dic['command'])
    if pt.ecdsa_verify(command, signature, str(dic['user'])):
        print('1')
        user=users_load(str(dic['user']))
        if 'cmd_num_biggest' not in user:
            user['cmd_num_biggest']=-1
        if int(dic['cmd_num']) > int(user['cmd_num_biggest']):
            user['cmd_num_biggest']=dic['cmd_num']
            users_save(str(dic['user']), user)
            print('2')
            out=execute_command(dic)
            print('2')
        else:
            return package({'type':'cmd_num_error', 'cmd_num':user['cmd_num_biggest']})
    else:
        out=package({'type':'error','message':bad_password_page.format(signature, command, '{}')})
    print('in func checksig')
    return out

#API functions
def deposit_address(dic):
    currency=str(dic['currency'])
    coin=currencies(currency)
    user=str(dic['user'])
    print('user: ' +str(user))
    address=coin.getaccountaddress(user)
    return package({'type':'success','deposit_address':address})
def user_data(dic):
    user=str(dic['user'])
    out=users_load(user)
    bitcoin=currencies('bitcoin')
    litecoin=currencies('litecoin')
    if user=='{}':
        out['comment']='No data yet applied to this user'
    else:
        out['user']=user
        out['bitcoin']=bitcoin.getbalance(str(dic['user']), 12)
        out['bitcoin_unconfirmed']=bitcoin.getbalance(dic['user'])
#        out['litecoin']=litecoin.getbalance(str(dic['user']), 12)
#        out['litecoin_unconfirmed']=litecoin.getbalance(dic['user'])
        out['litecoin']=0
        out['litecoin_unconfirmed']=0
    return package(out)
def withdraw(dic):
    user=str(dic['user'])
    amount=float(dic['amount'])
    to_address=str(dic['to_address'])
    currency=str(dic['currency'])
    coin=currencies(currency)
    current_money=float(coin.getbalance(user, 12))
    future_money=float(coin.getbalance(user))
    if current_money> dic['amount']:#This line is probably broken.
        coin.sendfrom(user, to_address, amount)
        out={'type':'success', 'message':"successfully withdrew funds"}
    else:
        out={'type':'success', 'message':"You do not have enough money. you only have {}, but you have {} more which will be ready for withdraw in the next 2 hours</p>".format(str(current_money),str(future_money-current_money))}
    return package(out)
def buy_bid(dic):
    cmd_num=str(dic['cmd_num'])
    buy_currency=str(dic['buy_currency'])
    buy_coin=currencies(buy_currency)
    buy_amount=float(dic['buy_amount'])
    sell_currency=str(dic['sell_currency'])
    sell_coin=currencies(sell_currency)
    sell_amount=float(dic['sell_amount'])
    user=str(dic['user'])
    current_money=float(sell_coin.getbalance(user, 12))
    future_money=float(sell_coin.getbalance(user))
    bought_so_far=0.0
    if [buy_currency, sell_currency].count('bitcoin')!=1:
        return package({'type':'error', 'message':'you must either buy bitcoin, or sell bitcoin, every time.'})        
    if current_money>= sell_amount:
#        sell_coin.move(user, "", sell_amount)
        available=available_bids(sell_currency, sell_amount, buy_currency, buy_amount)
        out={'type':'success', 'message':empty_page}
        print('available: ' +str(available))
        while len(available)>0 and buy_amount>bought_so_far:#buy entire bid
            owner_name=available[0]['owner']
            if buy_amount-bought_so_far>=float(available[0]['sell_amount']):
                bought_so_far+=float(available[0]['buy_amount'])
                sell_coin.move(user, owner_name, float(available[0]['buy_amount']))
                buy_coin.move("", user, float(available[0]['sell_amount']))
                append_to_trades(available[0])
                remove_bid(available[0])
                out['message']=out['message'].format("<p>successfully purchased a bid</p>{}")
            else:#buy part of a bid
                buy_coin.move("", user, buy_amount-bought_so_far)
                sell_coin.move(user, owner_name, (buy_amount-bought_so_far)*price(available[0]))
                def f(a, b):
                    return (b-a)/b
                p=f(buy_amount-bought_so_far, available[0]['buy_amount'])
                adjust_bid(available[0], p)
                bought_so_far=buy_amount
                out['message']=out['message'].format("<p>successfully purchased part of a bid</p>{}")
        if buy_amount-bought_so_far>0:
            print('user: ' +str(user))
            sell_coin.move(user, "", (buy_amount-bought_so_far)*price(dic))
            newbid={'buy_amount':buy_amount, 'sell_amount': sell_amount,'buy_currency':buy_currency ,'sell_currency':sell_currency ,'owner':user, 'cmd_num':cmd_num}
            newbid['price']=price(newbid)
            newbid['bid_id']=pt.sha256(json.dumps(newbid).encode('hex'))
            add2bids(newbid)
            out['message']=out['message'].format('<p>successfully submitted a bid</p>{}')
    else:
        return package({'type':'error', 'message':'not enough money'})
    return package(out)
def sell_bid(dic):
    bid_id=str(dic['bid_id'])
    user_name=str(dic['user'])
    user=users_load(user_name)
    bids=user['bids']
    for b in bids:
        if 'bid_id' not in b:
            user['bids'].remove(b)
            users_save(user_name, user)
        elif str(b['bid_id'])==str(bid_id) and b['owner']==user_name:
            coin=currencies(str(b['sell_currency']))
            coin.move("", user_name, float(b['sell_amount']))
            remove_bid(b)
            return package({'type':'success', 'message':'successfully un-submitted a bid'})
    return package({'type':'error', 'message':'<p>you do not own that bid</p>'})
#HTML
form='''
<form name="first" action="{}" method="{}">
<input type="submit" value="{}">{}
</form> {}
'''
newline='''<br />
{}'''
empty_page='<html><body>{}</body></html>'
def easyForm(link, button_says, moreHtml='', typee='post'):
    a=form.format(link, '{}', button_says, moreHtml, "{}")
    if typee=='get':
        return a.format('get', '{}')
    else:
        return a.format('post', '{}')
linkHome = easyForm('/', 'HOME', '', 'get')
def page1(dic):
    out=empty_page
    out=out.format('<p>It Works!!</p>{}')
    return out.format('')
#server
class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        def url2dic(junk):#for in 'get'
            junk=junk.split('&')
            dic={}
            for i in junk:
                a=i.split('=')
                if len(a)==2:
                    dic[a[0]]=a[1]
            return dic
        #       try:
        path=self.path
        if path == '/' or path[0:2] == '/?' :    
            if len(path)>1:
                dic=url2dic(path[2:])
            else:
                dic={}
                self.send_response(200)
                self.send_header('Content-type',    'text/html')
                self.end_headers()
                self.wfile.write(page1(dic))
                return    
        elif path[0:10]=='/checkSig?':
            print("IN CHECKSIG!")
            if len(path)>9:
                dic=url2dic(path[10:])
            print('dic: ' +str(dic))
            self.send_response(200)
            self.send_header('Content-type',    'text/html')
            self.end_headers()
            self.wfile.write(checkSig(dic))
            return
        else : # default: just send the file    
            filepath = self.path[1:] # remove leading '/'    
            if [].count(filepath)>0:
                #               f = open( os.path.join(CWD, filepath), 'rb' )
                #note that this potentially makes every file on your computer readable bny the internet
                self.send_response(200)
                self.send_header('Content-type',    'application/octet-stream')
                self.end_headers()
                self.wfile.write(f.read())
                #            f.close()
            else:
                self.send_response(200)
                self.send_header('Content-type',    'text/html')
                self.end_headers()
                self.wfile.write("<h5>Don't do that</h5>")
            return
        return # be sure not to fall into "except:" clause ?      
#        except IOError as e :  
#            print e
#            self.send_error(404,'File Not Found: %s' % self.path)
    def do_POST(self):
            print("path: " + str(self.path))
#         try:
            ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))    
            print(ctype)
            if ctype == 'multipart/form-data' or ctype=='application/x-www-form-urlencoded':    
               fs = cgi.FieldStorage( fp = self.rfile,
                                      headers = self.headers, # headers_,
                                      environ={ 'REQUEST_METHOD':'POST' })
            else: raise Exception("Unexpected POST request")
            self.send_response(200)
            self.end_headers()
            def fs2dic(fs):#for in "post"
                dic={}
                for i in fs.keys():
                    a=fs.getlist(i)
                    if len(a)>0:
                        dic[i]=fs.getlist(i)[0]
                    else:
                        dic[i]=""
                return dic
            dic=fs2dic(fs)
            if self.path=='/':
                self.wfile.write(page1(dic))
            elif self.path=='/checkSig':
                print('HERE')
                self.wfile.write(checkSig(dic))
            else:
                print('ERROR: path {} is not programmed'.format(str(self.path)))
def main():
   try:
      server = HTTPServer(('', PORT), MyHandler)
      print 'started httpserver...'
      server.serve_forever()
   except KeyboardInterrupt:
      print '^C received, shutting down server'
      server.socket.close()
if __name__ == '__main__':
   main()
