#!/usr/bin/env python
import sys
import getopt
import re, quopri, codecs
import vobject

def parse_vcf(f):
    """ 
        Parses a vcf string, potentially containing many vcards 
        @returns: A list of Contacts 
    """ 
    infile = open(f,"r")
    string = infile.read()
    infile.close()

    string  = vcard2vcf3(string)
    contacts = [] 
    for vobj in vobject.readComponents(string, True, True, True, True):
        try:
            contacts.append(vobj)
        except vobject.base.ParseError:
            print "errore Parse"
        
    return contacts

def vcard2vcf3(string):
    string = re.compile('TEL;(\w+):',re.IGNORECASE).sub(r'TEL;TYPE=\1:', string)
    string = re.compile('X-messaging/(\w+)-All',re.IGNORECASE).sub(r'X-\1',string)
    # indent b64 multi-line: use this f* re.M
    string = re.compile('^([+=A-Za-z0-9/]+\r\n)',re.MULTILINE).sub(r' \1',string)
    #string = re.compile('^(.*);ENCODING=QUOTED-PRINTABLE([:;].*)').sub(r'\1')
    return string
    
    
def dedupe(allContacts):
    noDups=[]
    for v in allContacts:
        noDups=isInArray(v, noDups)
    
    return noDups

    
# this function return a hashname for the vObj
def hashName(vObj, swap=False):
    name = vObj.n.value
    ret = ""
    
    if name.__class__.__name__ == 'Name':
        if swap:
            if name.family:
                ret += name.family.capitalize()
            if name.given:
                ret += name.given.capitalize()
        else:            
            if name.given:
                ret += name.given.capitalize()
            if name.family:
                ret += name.family.capitalize()
    elif name.__class__.__name__ == 'unicode':        
        for str in name.split():
            if swap:
                ret = str.capitalize()+ret
            else:
                ret = ret+str.capitalize()
            
    #print "\t\tdebug:" + ret
    return ret    
    
# two contacts are the same if
#   same name
#   share one mail address
#   share one phone number (todo not work phone number)
def areTheSame(first, second):    
    if ((hashName(first) == hashName(second)) or
        (hashName(first) == hashName(second,True)) ):
        return True
    
    for field in "TEL", "EMAIL":
        ff = getFields(first, field)
        fs = getFields(second, field)
        intersection=filter(lambda x:x in ff, fs)
        if intersection:
            return True
            #print "field: ",field," ff=",ff,"fs=",fs, "intersect=",intersection
    
    
   
#retrieve a given field from a contact
# ex getField(vobj, "TEL")
# ex getField(vobj, "EMAIL")
def getFields(vobj, string, full=False):
    fields=[]
    for i in vobj.getSortedChildren():
        if i.name==string:
            if string=="TEL" and not i.value.startswith("+"):
                i.value = "+39" + i.value
            if full:
                fields.append(i)
            else:
                fields.append(i.value)
            
    return fields
    
#if contact is still in array...
def isInArray(object, array):
    for a in array:
        if (areTheSame(a,object)):
            #merg'em and validate
            print "still there"
            print object.serialize()
            print a.serialize()
            a = mergeItems(a,object)
            return array
            
    try:
        object.serialize()
    except vobject.base.ValidateError:
        try:
            object.n
        except AttributeError:
            print "added n"
            object.n.value = vobject.vcard.Name(family="Nemo")
        #object.prettyPrint()   
        try:
            object.fn
        except AttributeError:
            print "added fn to "+str(object.n)
            object.add("fn")
            object.fn.value = "Nemo"        


    #object.prettyPrint()
    array.append(object)
            
    return array
    
# merge two items
# we could use fuzzy results to select the %
def mergeItems(one,two):
    print "mergeItems()"
    one.prettyPrint()
    two.prettyPrint()
    
    #find a smart way to
    # merge two Formatted Name http://tools.ietf.org/html/rfc2426#section-3.1.1
    try:
        if len(two.fn.value) > len(one.fn.value):
            one.add("nickname").value=one.fn.value
            one.fn.value=two.fn.value
    except:
        pass
     
    #fmerge Name http://tools.ietf.org/html/rfc2426#section-3.1.2
    # this attribute is REQUIRED and can be multi-valued
    try:
        if  (hashName(one) != hashName(two))\
            and (hashName(one) != hashName(two, True)):
            #name is almost the same, use the first one
            one.add("n").value = two.n.value
    except:
        pass

        
        
    #join mail address and phone number
    for field in "TEL", "EMAIL":
        ot=getFields(one,field, True)
        tt=getFields(two,field, True)
        nt=filter(lambda x:x not in ot, tt)
        for i in nt:
            one.add(i)
    print "mergedItem:"
    one.prettyPrint()
 
    return one

def main():
    # parse command line options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hv", ["help", "verbose"])
    except getopt.error, msg:
        print msg
        print "for help use --help"
        sys.exit(2)
        
    for i in opts:
        print "opts:"+i[0]
        
    for i in args:
        print "args:"+i
    
    files = args
    allContacts = []
    for f in files:
        print "file:"+f
        try:
            allContacts=parse_vcf(f)
        except IOError:
            print "errore: file not found"
            sys.exit(2)  
            
    myContacts=dedupe(allContacts)
    outfile = open("deduped_addressbook.vcf","w+")
    print "Creating new addressbook: deduped_addressbook.vcf"
    for i in myContacts:
        #print i.serialize()
        outfile.write(i.serialize())
    print "done"
            
        
if __name__ == "__main__":
    main()
