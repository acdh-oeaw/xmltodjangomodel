"""
convert a xml file to django models
"""
# pylint: disable=too-many-locals, import-error
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
    "choiceField": "choicefield",
}

jinja_env = Environment(loader=FileSystemLoader("templates/"), autoescape=False)

# get input and output files
parser = argparse.ArgumentParser()
parser.add_argument("infile", type=argparse.FileType("r"))
parser.add_argument(
    "outfile", nargs="?", type=argparse.FileType("w"), default=sys.stdout
)
parser.add_argument("-j", "--json", action="store_true")
args = parser.parse_args()


def extractinfo(infile):
    """Extract the relevant fields from the xml file an return a dict"""
    tree = etree.parse(infile)

    relations = {}
    classes = {}

    for cls in tree.xpath("//model/classes/class"):
        cls_id = cls.xpath("./@ID")[0]
        definition = cls.xpath("./definition//text()")
        definition = "".join(definition)
        classes[cls_id] = {"definition": definition.strip(), "properties": {}}

        for prp in cls.xpath("./properties/property"):
            prp_id = prp.xpath("./@ID")[0]
            propertyname = prp_id.split(".")[-1]
            if "date_written" in prp_id or prp_id.split(".")[-1] == "name":
                continue

            datatype = prp.xpath("./datatypeName/@target")[0]
            classes[cls_id]["properties"][propertyname] = {
                "name": prp.xpath("./name/text()")[0],
                "note": prp.xpath("./note/text()")[0],
                "datatype": map_fields[datatype],
            }
            vocabref = prp.xpath("./datatypeName/@vocabRef")
            if datatype == "choiceField" and len(vocabref) > 0:
                lst_choices = tree.xpath(
                    f"//vocab[@ID = '{vocabref[0]}']/values/list/item/text()"
                )
                classes[cls_id]["properties"][propertyname]["length"] = max(
                    len(x) for x in lst_choices
                )
                classes[cls_id]["properties"][propertyname]["choices"] = lst_choices

        for rel in cls.xpath("./relations/relation"):
            src = rel.xpath("./sourceClass/@target")[0].split(" ")
            trgt = rel.xpath("./targetClass/@target")[0].split(" ")
            name = rel.xpath("./name/text()")[0]
            # get the ID from the relation and normalize it in case there are any umlauts
            # then change the CapWords id to lowercase separated with an underscore
            orid = (
                unicodedata.normalize("NFKD", rel.get("ID"))
                .encode("ascii", "ignore")
                .decode()
            )
            rid = "".join([f"_{x.lower()}" if x.isupper() else x for x in orid])[1:]
            name_reverse = rel.xpath("./reverseName/text()")[0]
            if rid not in relations:
                relations[rid] = {
                    "name": name,
                    "name_reverse": name_reverse,
                    "subjects": src,
                    "objects": trgt,
                    "orid": orid
                }
            else:
                if relations[rid]["name_reverse"] != name_reverse:
                    print("You got a mismatch in vocabs names")
                else:
                    if src not in relations["name"]["subjects"]:
                        relations["name"]["subjects"].extend(src)
                    if trgt not in relations["name"]["objects"]:
                        relations["name"]["objects"].extend(trgt)

    return {"classes": classes, "relations": relations, "filename": infile.name}


result = extractinfo(args.infile)

if args.json:
    print(json.dumps(result, indent=3))

models = jinja_env.get_template("models.py.j2").render(result)

args.outfile.write(models)
