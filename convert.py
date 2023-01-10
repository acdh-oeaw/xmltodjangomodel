"""
convert a xml file to django models
"""
import argparse
import json
import sys
import unicodedata

from lxml import etree
from jinja2 import Environment, FileSystemLoader

map_fields = {
    "float": "floatfield",
    "int": "integerfield",
    "shortText": "charfield",
    "longText": "textfield",
    "choiceField": "choicefield"
}

jinja_env = Environment(loader=FileSystemLoader('templates/'), autoescape=False)

# get input and output files
parser = argparse.ArgumentParser()
parser.add_argument('infile', type=argparse.FileType('r'))
parser.add_argument('outfile', nargs='?', type=argparse.FileType('w'), default=sys.stdout)
parser.add_argument('-j', '--json', action='store_true')
args = parser.parse_args()

tree = etree.parse(args.infile)

relations = {}
classes = {}

for cls in tree.xpath("//model/classes/class"):
    cls_id = cls.xpath("./@ID")[0]
    classes[cls_id] = {}

    for prp in cls.xpath("./properties/property"):
        prp_id = prp.xpath("./@ID")[0]
        propertyname = prp_id.split(".")[-1]
        if "date_written" in prp_id or prp_id.split(".")[-1] == "name":
            continue
        datatype = prp.xpath("./datatypeName/@target")[0]
        vocabref = prp.xpath("./datatypeName/@vocabRef")
        classes[cls_id][propertyname] = {'datatype': map_fields[datatype]}
        if datatype == "choiceField" and len(vocabref) > 0:
            lst_choices = tree.xpath(f"//vocab[@ID = '{vocabref[0]}']/values/list/item/text()")
            classes[cls_id][propertyname]['length'] = max(len(x) for x in lst_choices)
            classes[cls_id][propertyname]['choices'] = lst_choices

    for rel in cls.xpath("./relations/relation"):
        src = rel.xpath("./sourceClass/@target")[0].split(" ")
        trgt = rel.xpath("./targetClass/@target")[0].split(" ")
        name = rel.xpath("./name/text()")[0]
        rid = unicodedata.normalize('NFKD', rel.get('ID')).encode('ascii', 'ignore').decode()
        rid = ''.join([f"_{x.lower()}" if x.isupper() else x for x in rid])[1:]
        name_reverse = rel.xpath("./reverseName/text()")[0]
        if rid not in relations:
            relations[rid] = {
                "name": name,
                "name_reverse": name_reverse,
                "subjects": src,
                "objects": trgt,
                }
        else:
            if relations[rid]["name_reverse"] != name_reverse:
                print("You got a mismatch in vocabs names")
            else:
                if src not in relations["name"]["subjects"]:
                    relations["name"]["subjects"].extend(src)
                if trgt not in relations["name"]["objects"]:
                    relations["name"]["objects"].extend(trgt)

result = {'classes': classes, 'relations': relations, 'filename': args.infile.name }
if args.json:
    print(json.dumps(result, indent=3))

models = jinja_env.get_template('models.py.j2').render(result)

args.outfile.write(models)
