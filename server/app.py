"""My Family App."""
from flask import Flask, jsonify, request, json
from flask.ext.restful import Api, Resource, fields, marshal, reqparse
from py2neo import Graph, authenticate, Relationship
from flask.ext.cors import CORS
import os
import time
import ssl

context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
context.load_cert_chain('/etc/nginx/ssl/nginx.crt', '/etc/nginx/ssl/nginx.key')

app = Flask(__name__)
app.config['BUNDLE_ERRORS'] = True
api = Api(app)
CORS(app)

url = os.environ.get('GRAPHENEDB_URL', 'http://localhost:7474')
username = os.environ.get('NEO4J_USERNAME')
password = os.environ.get('NEO4J_PASSWORD')

if username and password:
    authenticate(url.strip('http://'), username, password)

graph = Graph(url + '/db/data/')

tree_fields = {
    'name': fields.String,
    'descr': fields.String,
    'people': fields.Url('persons', absolute=True, scheme='https'),
    'uri': fields.Url('tree', absolute=True, scheme='https')
}

person_fields = {
    'name': fields.String,
    'dob': fields.String,
    'sex': fields.String,
    'parents': fields.Url('parents', absolute=True, scheme='https'),
    'siblings': fields.Url('siblings', absolute=True, scheme='https'),
    'children': fields.Url('children', absolute=True, scheme='https'),
    'uri': fields.Url('person', absolute=True, scheme='https')
}

class TreeListApi(Resource):
    """Displaying all the family trees."""

    def __init__(self):
        """Init method."""
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('name', type=str, required=True,
                                   help='No family tree name provided.',
                                   location='json')
        self.reqparse.add_argument('descr', type=str, required=False,
                                   help='Describe the family tree.',
                                   location='json')
        super(TreeListApi, self).__init__()

    def get(self):
        """Retrieve all Trees."""
        query = """
            match (p:Tree)
            return p.name, p.descr, id(p)
            order by p.name
            """
        result = graph.cypher.execute(query)
        output = []
        for x in result:
            tree = marshal({"name": x[0], "descr": x[1], "tid": x[2]}, tree_fields)
            output.append(tree)
        return output

    def post(self):
        """Create a new Tree."""
        tree = {}
        args = self.reqparse.parse_args()
        for k, v in args.items():
            if v is not None:
                tree[k] = v

        query = """
            CREATE (p:Tree {name: {name}, descr: {descr}})
            RETURN id(p)
            """
        result = graph.cypher.execute(query, tree)
        tree['tid'] = result[0][0]
        return marshal(tree, tree_fields)
        # return tree
        
class TreeApi(Resource):
    """docstring for TreeApi."""

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('name', type=str, location='json')
        self.reqparse.add_argument('descr', type=str, location='json')
        super(TreeApi, self).__init__()

    def get(self, tid):
        """."""
        query = "match(p:Tree) where id(p)={id} return p.name, p.descr"
        result = graph.cypher.execute(query, {"id": tid})
        tree = {"name": result[0][0], "descr": result[0][1], "tid": tid}
        return marshal(tree, tree_fields)



class PersonListApi(Resource):
    """Displaying all the persons and adding to the list."""

    def __init__(self):
        """Init method."""
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('name', type=str, required=True,
                                   help='No name provided',
                                   location='json')
        self.reqparse.add_argument('dob', type=int, required=True,
                                   help='Enter your date of birth ',
                                   location='json')
        self.reqparse.add_argument('sex', type=str, required=True,
                                   help='Enter your sex',
                                   location='json')
        super(PersonListApi, self).__init__()

    def get(self, tid):
        """Retrieve all people for a tree."""
        query = """
            match (p:Person)
            return p.name, p.dob, p.sex, id(p)
            order by p.name
            """
        result = graph.cypher.execute(query)
        output = []
        for x in result:
            # dob = time.strftime("%c", time.gmtime(x[1]))
            person = marshal(
                {"name": x[0], "dob": x[1], "sex": x[2],
                 "pid": x[3]}, person_fields)
            output.append(person)
        return output

    def post(self):
        """Create a new Person."""
        person = {}
        args = self.reqparse.parse_args()
        # person = {
        #     "name": args['name'],
        #     "dob": args['dob'],
        #     "sex": args['sex'],
        # }
        for k, v in args.items():
            if v is not None:
                person[k] = v

        query = """
            CREATE (p:Person {name: {name}, dob: {dob}, sex: {sex}})
            RETURN id(p)
            """
        result = graph.cypher.execute(query, person)
        person['id'] = result[0][0]
        # person['dob'] = result[0][1] # time.strftime("%c", time.gmtime(person['dob']))
        return marshal(person, person_fields)


class PersonApi(Resource):
    """docstring for PersonApi."""

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('name', type=str, location='json')
        self.reqparse.add_argument('dob', type=int, location='json')
        self.reqparse.add_argument('sex', type=str, location='json')
        super(PersonApi, self).__init__()

    def get(self, pid):
        """."""
        result = graph.cypher.execute(
            "match(p: Person) where id(p)={id}\
            return p.name, p.dob, p.sex", {"id": pid})
        # dob = time.strftime("%c", time.gmtime(result[0][1]))
        person = {"name": result[0][0], "dob": result[0][1],
                  "sex": result[0][2], "id": pid}
        return marshal(person, person_fields)

    def put(self, pid):
        """Updating a Person's details."""
        person = {}
        result = graph.cypher.execute(
            "MATCH (p:Person) WHERE id(p)={id} RETURN p", {"id": pid})
        person = result[0][0].properties
        args = request.json  # self.reqparse.parse_args()
        for k, v in args.items():
            if v is not None:
                person[k] = v
        person['id'] = id
        return marshal(person, person_fields)

    def delete(self, pid):
        """Delete a person and all his relations from the database."""

        query = "MATCH (n) WHERE id(n)={id} DETACH DELETE n"
        graph.cypher.execute(query, {"id": pid})
        return jsonify({"message": "Record %d deleted!" % pid})


class ParentListApi(Resource):
    """Retrieve a person's parents."""

    def __init__(self):
        """initialise parser."""
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('name', type=str, required=True,
                                   help='No name provided',
                                   location='json')
        self.reqparse.add_argument('dob', type=int, required=True,
                                   help='Enter your date of birth ',
                                   location='json')
        self.reqparse.add_argument('sex', type=str, required=True,
                                   help='Enter your sex',
                                   location='json')
        super(ParentListApi, self).__init__()

    def get(self, id):
        """Retrieve a person's parents."""
        query = """
            MATCH (a:Person)<-[r:MOTHER_OF|FATHER_OF]-(b)
            WHERE id(a)={id}
            RETURN b.name, b.dob, b.sex, id(b)
            """
        result = graph.cypher.execute(query, {"id": id})
        parents = []
        for parent in result:
            person = {"name": parent[0], "dob": parent[
                1], "sex": parent[2], "id": parent[3]}
            person = marshal(person, person_fields)
            parents.append(person)
            # if parent[2] == "F":
            #     parents['mother'] = person
            # elif parent[2] == "M":
            #     parents['father'] = person
        return {"parents": parents}

    def post(self, id):
        """Add a child's parent provided that there aren't 2 already."""

        childname = graph.cypher.execute("Match (n:Person) where id(n)={id} return n.name", {"id": id})[0][0]
        query = "MATCH (a:Person)<-[r:MOTHER_OF|FATHER_OF]-(b) WHERE id(a)={id} RETURN count(*)"
        result = graph.cypher.execute(query, {"id": id})

        if len(result) == 0 or (result[0][0] < 2):
            args = self.reqparse.parse_args()
            # try:
            #     args = self.reqparse.parse_args()
            # except:
            #     return jsonify({'error': 'please supply name, dob, sex'})
            if args['sex'] == "M":
                rel = "FATHER_OF"
            elif args['sex'] == "F":
                rel = "MOTHER_OF"
            child = graph.merge_one("Person", "name", childname)
            parent = graph.merge_one("Person", "name", args['name'])
            graph.create_unique(Relationship(parent, rel, child))
            for k, v in args.iteritems():
                if k != 'name':
                    parent[k]=v
            graph.push(parent)
            return jsonify({'message': 'Parent has been added successfully.'})
        else:
            return jsonify({'error': 'Person has 2 parents already!!'})

class SiblingListApi(Resource):
    """docstring for SiblingsApi."""
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('name', type=str, required=True,
                                   help='No name provided',
                                   location='json')
        self.reqparse.add_argument('dob', type=int, required=True,
                                   help='Enter your sex',
                                   location='json')
        self.reqparse.add_argument('sex', type=str, required=True,
                                   help='Enter your sex',
                                   location='json')
        super(SiblingListApi, self).__init__()
    
    def get(self, id):
        query = """
            MATCH (a:Person)-[r:SIBLING_OF]-(b:Person) 
            WHERE id(a) = {id}
            RETURN b.name as name, b.dob as dob, b.sex as sex, id(b) as id
            """
        result = graph.cypher.execute(query, {"id": id})
        siblings = []
        for sibling in result:
            person = {"name": sibling.name, "dob": sibling.dob,
                "sex": sibling.sex, "id": sibling.id}
            person = marshal(person, person_fields) 
            siblings.append(person)
            # if sibling.sex == "F":
            #     siblings['sister'] = person
            # elif sibling.sex == "M":
            #     siblings['brother'] = person
        return {"siblings": siblings}

    def post(self, id):
        """Add a child's brother/sister."""

        # name = graph.cypher.execute("Match (n:Person) where id(n)={id} return n.name", {"id": id})[0][0]
        query = "MATCH (a:Person)-[r:SIBLING_OF]-(b:Person) WHERE id(a)={id} RETURN a.name as me, b.name as name"
        result = graph.cypher.execute(query, {"id": id})
        args = self.reqparse.parse_args()
        # if args['sex'] == "M":
        #     rel = "BROTHER_OF"
        # elif args['sex'] == "F":
        #     rel = "SISTER_OF"
        child = graph.merge_one("Person", "name", result[0].me)
        sibling = graph.merge_one("Person", "name", args['name'])
        graph.create_unique(Relationship(sibling, "SIBLING_OF", child))
        for other_sibling in result:
            br = graph.merge_one("Person", "name", other_sibling.name)
            graph.create_unique(Relationship(sibling, "SIBLING_OF", br))
        for k, v in args.iteritems():
            if k != 'name':
                sibling[k]=v
        graph.push(sibling)
        return jsonify({'message': 'Sibling has been added successfully.'})

class ChildrenListApi(Resource):
    """docstring for ChildrenListApi."""

    def __init__(self):
        """initialise parser."""
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('name', type=str, required=True,
                                   help='No name provided',
                                   location='json')
        self.reqparse.add_argument('dob', type=int, required=True,
                                   help='Enter your date of birth ',
                                   location='json')
        self.reqparse.add_argument('sex', type=str, required=True,
                                   help='Enter your sex',
                                   location='json')
        super(ChildrenListApi, self).__init__()
        
    def get(self, id):
        query = """
            MATCH (a:Person)-[r:MOTHER_OF|FATHER_OF]->(b:Person) 
            WHERE id(a) = {id}
            RETURN b.name as name, b.dob as dob, b.sex as sex, id(b) as id
            """
        result = graph.cypher.execute(query, {"id": id})
        children = []
        for child in result:
            person = {"name": child.name, "dob": child.dob,
                "sex": child.sex, "id": child.id}
            person = marshal(person, person_fields) 
            children.append(person)
        return {"children": children}
        
api.add_resource(
    TreeListApi,
    '/family/api/v2.0/trees',
    endpoint='trees')
    
api.add_resource(
    TreeApi,
    '/family/api/v2.0/trees/<int:tid>',
    endpoint='tree')

api.add_resource(
    PersonListApi,
    '/family/api/v2.0/trees/<int:tid>/persons',
    endpoint='persons')

api.add_resource(
    PersonApi,
    '/family/api/v2.0/trees/<int:tid>/persons/<int:pid>',
    endpoint='person')

api.add_resource(
    ParentListApi,
    '/family/api/v2.0/trees/<int:tid>/persons/<int:pid>/parents',
    endpoint='parents')

api.add_resource(
    SiblingListApi,
    '/family/api/v2.0/trees/<int:tid>/persons/<int:pid>/siblings',
    endpoint='siblings')

api.add_resource(
    ChildrenListApi,
    '/family/api/v2.0/trees/<int:tid>/persons/<int:pid>/children',
    endpoint='children')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True, ssl_context=context)
