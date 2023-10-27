import json
import copy

f = json.load(open('./json-schema/json-schema.json'))

def fetch_lobs(json_file,prisma_models):
    print(prisma_models)
    if prisma_models[0] == 'order':
        business = json_file['definitions']['Order']['properties']['businessSubType']['enum']
        
        if 'FnB' in business:
            business = list(map(lambda x: x.replace('FnB', 'foodAndBeverages'), business))

        business_files = json_file['definitions']['OrderDetail']['properties'].keys()
        
        lob=[]

        for buss in business:
            for orderDetail_col in business_files:
                
                if buss[:3].lower() in orderDetail_col[:3].lower():
                    lob.append(orderDetail_col)
        
        return lob
    else:return [""]

def go_to_path(path,full_document):
    """ Takes input path as string then goes to the location in full_document 
        and gives output as object present inside full_document 

        Parameters
        ----------
        path : String
        full_document : json file genereate by prisma-json-schema-generator
        Example
        -------
        path : "#/definitions/Order"
        full_doucment : "{ "$schema": "http://json-schema.org/draft-07/schema#",
                            "definations":{...}
                            "type": "object",
                            "properties" :{...}
                        }"
        Output
        ------
        "{"type":"string",
            "properties":"{..}"
        }"
    """

    path = path.split('/')[-1]
    data = f.get('definitions').get(path)
    return data


def maping(data_type):
    """

    """
    if isinstance(data_type,list) and len(data_type)>0:
        
        ranking = {"string":1,"timestamp":2,"number":4,"integer":4,"double":3,"null":6,"boolean":5,"object":-1,"array":7}
       
        input_ranking = {}

        for i in data_type: input_ranking[i] = ranking[i]

        min_value = min(input_ranking.values())

        for key,value in input_ranking.items(): 
            if value == min_value: 
                if key == 'number':return 'double'
                elif key =='null':return 'string'
                else: return key

    elif data_type == 'number': return 'double'

    elif data_type == 'null': return 'string'

    else: return data_type


def maping_array(array_data): return {"containsNull":True,"elementType":maping(array_data),"type":"array"}

#------------------------------------------------  


def perse(data,f):
    """
    """
    result=[]
  
    if 'properties' in data :
        for field in data['properties']:
            dct = { "metadata": {},
            "name": "str",
            "nullable": True,
            "type": "string" }

            dct['name'] = field 

            if '$ref' in data['properties'][field]:
                dct['type'] = maping(perse(go_to_path(data['properties'][field]['$ref'],f),f))
                
            elif 'type' in data['properties'][field]:
                
                if data['properties'][field]['type'] == 'array' :
                    if 'enum' in data['properties'][field]:
                        dct['type'] = maping_array('string')
                    
                    elif 'items' in data['properties'][field]:
                        if '$ref' in data['properties'][field]['items']:
                            dct['type'] = maping_array(perse(go_to_path(data['properties'][field]['items']['$ref'],f),f))
                        
                        elif 'type' in data['properties'][field]['items'] :
                            dct['type'] = maping_array(data['properties'][field]['items']['type'])


                elif 'format' in data['properties'][field]:
                    if data['properties'][field]['format'] == 'date-time': dct['type'] = "timestamp"
                
                else:
                    dct['type'] = maping(data['properties'][field]['type'])

            elif 'anyOf' in data['properties'][field]:
                dct['type'] = maping(perse(go_to_path(data['properties'][field]['anyOf'][0]['$ref'],f),f))
            #print(dct)
            result.append(dct)
    return {"fields":result,"type":"struct"}


def lobWiseOutput(fulldoc, bussinesstype,lob_list):
    mandatry_list = []
    orderDetail_no = 0
    counter =0
    for i in fulldoc['fields']:
        counter+=1
        #print(i['name'])
        if i['name'] == 'orderDetail':
            orderDetail_no = counter
            for j in fulldoc['fields'][counter-1]['type']['fields']:
                if j['name'] not in lob_list:
                    mandatry_list.append(j['name'])
    
    mandatry_list.append(bussinesstype)

    temp_doc=copy.deepcopy(fulldoc)
   
    for i in fulldoc['fields'][orderDetail_no-1]['type']['fields']:

        if i['name'] not in mandatry_list:
            temp_doc['fields'][orderDetail_no-1]['type']['fields'].remove(i)
    
    return temp_doc

def apply_parse_updates(pyspark_schema,collection):
    parse_config = json.load(open('parse_updates.json'))

    if parse_config['apply_updates']['required']:
        for config in parse_config['apply_updates']['parsing_configs']:
            if config['collection_name'] == collection:
                
                # Keys rename
                if config['keys_rename']['required']:
                    for key,value in config['keys_rename']['keys'].items():
                        print('will replace key',key,' as value',value)
    return pyspark_schema



if __name__=="__main__":
    
    prisma_models = [i for i in f['properties'].keys() if i!= 'demo']

    withallLob_persed = perse(go_to_path(f['properties'][prisma_models[0]]['$ref'],f),f)
    withallLob_persed = apply_parse_updates(withallLob_persed,prisma_models[0])

    lob_list = fetch_lobs(f,prisma_models)

    for i in lob_list:
        if prisma_models[0] == 'order':
            output = lobWiseOutput(withallLob_persed,i,lob_list)
        else :
            output = withallLob_persed
        
        name = prisma_models[0]+"_Airport_"+i+"_schema.json"
        
        with open(''+name,'w') as fp:
            json.dump(output,fp,indent=4)
        
