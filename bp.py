from time import time
from flask import Flask, jsonify, request
from uuid import uuid4
from urllib.parse import urlparse #for locate a node 
from Crypto.Hash import keccak            #الگوریتم هش keccak256
import hashlib                           # الگورتم هش sha256 
import requests 
import json
import sys

#programmer : Aria_pourmand
#E-mail : ariapour77@gmial.com
#instagram : @ariapmd

class blockchain():

    def __init__(self):
        
        self.chain = []
        self.current_trxs = []   #mem pool
        self.new_block(proof = 100, previous_hash=1)
        self.nodes= set() #از ست استفاده می کنیم تا مجموعه تعریف کنیم تا نود تکراری نداشته باشیم

    def new_block(self, proof, previous_hash=None): #create a new block
        #we define previous_hash = none becuase we have problem in genesis block
        block = {
            'index' : len(self.chain) + 1,
            'timestamp' : time(),
            'trxs' : self.current_trxs,
            'proof': proof,
            'previous_hash':self.hash(self.chain[:-1]) or previous_hash
        }

        self.current_trxs = []
        self.chain.append(block)
        return block

    def new_trx(self, sender, recipient, amount):  #add a new trx to the mempool
        self.current_trxs.append({'sender':sender , 'recipient':recipient,'amount':amount})

        return self.last_block['index'] + 1 

    @staticmethod #hash() just callable by this class and subfunctions of this class
    def hash(block):  #hash a block
        #چون در پایتون ترتیب ذخیره داده مهم نیست ولی در بالاکچین مهم است از دامپس به جای دامپ استفاده کردم تا ترتیب حفظ شود
        #مشخصات یک بلاک رو به استرینگ تبدیل می کنیم و بعد اون استرینگ رو هش میکنیم 
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def register_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        last_block = chain[0]
        current_index= 1 #چون فعلی را صفر درنظر گرفتیم و بعدی را با ان مقایسه میکنیم
        while current_index <len(chain):
            block = chain[current_index]
            #if someone has changes blocks:
            if block['previous_hash'] != self.hash(last_block):
                return False
            #if not found a fine nonce : 
            if not self.valid_proof(last_block['proof'], block['proof']):
                return false

            last_block = block
            current_index += 1 
        
        return True

    #check the chain is valid or not :
    def resolve_conflicts(self):
        neighbours = self.nodes
        new_chain = None

        max_lenght = len(self.chain)
        for node in neighbours :
            response = requests.get(f"http://{node}/chain")
            if response.status_code== 200 :
                length = response.json()['length']
                chain = response.json()['chain']

            #در بیت کوین ماینری که بزرگترین زنجیره را تولید میکند معتبر است 
            #یعنی ماینری که بیشتر کار کرده بلاک های آن معتبر است 
            #این یکی از خطرات حمله 51 درصد است 
                if length > max_lenght and self.valid_chain(chain):
                    max_lenght = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True
        
        return False
    
    @property #continuos call last_blockchain()
    def last_block(self): #return last block of chain
        return self.chain[-1]

    @staticmethod
    def valid_proof(last_proof, proof): # check if this proof valid or not
        this_proof = f'{proof}{last_proof}'.encode()
        this_proof_hash = hashlib.sha256(this_proof).hexdigest()
        return this_proof_hash[:4] == "0000" 
        # 0000 --> network basic difficualty

    #set a proof(nonce) --> generate a block --> calcatulate sha256 of block --> if last 4char === 0000 : ok & get rewards
    def proof_of_work(self, last_proof): #show which miner work hunestly
        proof = 0 
        while self.valid_proof(last_proof, proof) is False :
            proof += 1
        
        return proof


#flask
app = Flask(__name__) #standard
node_id = str(uuid4())



blockchain = blockchain()

@app.route('/mine')
def mine(): #mine a block & add it to the chain
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)
    #reward of mining
    blockchain.new_trx(sender = "0", recipient=node_id, amount=3.25)
    
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)
    
    res={
        'message':'new block created',
        'index' : block['index'],
        'trxs':block['trxs'],
        'proof':block['proof'],
        'previous_hash':block['previous_hash']
    }

    return jsonify(res), 200



@app.route('/trxs/new', methods=['POST'])
def new_trx():  #will add a new trx by getting sender, recipient, amount
    values = request.get_json()
    this_block= blockchain.new_trx(values['sender'], values['recipient'], values['amount'])
    res = {'message':f'will be added to block {this_block}' }
    return jsonify(res), 201  #201 means done/finish

@app.route('/chain')
def full_chain(): # return full chain
    res = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }

    return jsonify(res), 200  #200 for return message to show function works fine

@app.route('/nodes/register' , methods= ['POST'])
def register_node():
    values = request.get_json()
    nodes = values.get("nodes")

    for node in nodes :
        blockchain.register_node(node)

    res = {"message": "nodes added",
            "total_node": list(blockchain.nodes)}

    return jsonify(res), 201 # 201 : create


@app.route('/nodes/resolve')
#هروقت فراخوانی شد به همه نود ها وصل شو زنجیره ان ها را بگیر طولانی ترین و معتبرترین آن را به عنوان زنجیره مرجع قرار بده
def consensus():
    replaced = blockchain.resolve_conflicts()
    if replaced:
        res={'message': 'replaced' ,
               'new_chain': blockchain.chain }
    else :
        res = {'message':'my chain the best!!',
                'chain':blockchain.chain}

    return jsonify(res), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=sys.argv[1])

