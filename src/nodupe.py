#!/usr/bin/env python
#
#    Copyright (C) 2014 Loïc CORBASSON <loic.corbasson@gmail.com>,
#      based on code from NoDupe <https://code.google.com/p/nodupe/>
#      copyright (C) 2008 Roberto POLLI <robipolli@gmail.com>.
#
#    This file is part of VCardDedupe.
#
#    VCardDedupe is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License version 2
#    as published by the Free Software Foundation..
#
#    VCardDedupe is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with VCardDedupe.  If not, see <http://www.gnu.org/licenses/>.
#
import sys
import getopt
import re
import quopri
import codecs
import vobject


def parseVcf(f):
    """ 
        Parses a vcf string, potentially containing many vcards 
        @returns: A list of Contacts 
    """
    infile = open(f, "r")
    string = infile.read()
    infile.close()

    string = vcard2vcf3(string)
    contacts = []
    for vobj in vobject.readComponents(string, True, True, True, True):
        try:
            contacts.append(vobj)
        except vobject.base.ParseError:
            print "Error: Could not parse VObject"

    return contacts


def vcard2vcf3(string):
    string = re.compile(
        'TEL;(\w+):', re.IGNORECASE).sub(r'TEL;TYPE=\1:', string)
    string = re.compile(
        'X-messaging/(\w+)-All', re.IGNORECASE).sub(r'X-\1', string)
    # indent b64 multi-line: use this f* re.M
    string = re.compile(
        '^([+=A-Za-z0-9/]+\r\n)', re.MULTILINE).sub(r' \1', string)
    #string = re.compile('^(.*);ENCODING=QUOTED-PRINTABLE([:;].*)').sub(r'\1')
    return string


def dedupe(allContacts):
    noDupes = []
    for v in allContacts:
        noDupes = isInArray(v, noDupes)

    return noDupes


# This function return a hashname for the vObj
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
                ret = str.capitalize() + ret
            else:
                ret = ret + str.capitalize()

    # print "\t\tdebug:" + ret
    return ret

# two contacts are the same if
#   same name
#   share one mail address
#   share one phone number (todo not work phone number)


def areTheSame(first, second):
    # Check if we have the same name (even if swapped)
    if ((hashName(first) == hashName(second)) or
            (hashName(first) == hashName(second, True))):
        return True

    for field in "TEL", "EMAIL":
        ff = getFields(first, field)
        fs = getFields(second, field)
        intersection = filter(lambda x: x in ff, fs)
        if intersection:
            return True
            # print "field: ",field," ff=",ff,"fs=",fs,
            # "intersect=",intersection


# retrieve a given field from a contact
# ex getFields(vobj, "TEL")
# ex getFields(vobj, "EMAIL")
def getFields(vobj, string, full=False):
    fields = []
    for i in vobj.getSortedChildren():
        if i.name == string:
            if string == "TEL" and not i.value.startswith("+"):
                    # TODO default phone
                i.value = "+39" + i.value
            if full:
                fields.append(i)
            else:
                fields.append(i.value)

    return fields

# if contact is still in array...


def isInArray(object, array):
    for a in array:
        if (areTheSame(a, object)):
            # merg'em and validate
            print "still there"
            print object.serialize()
            print a.serialize()
            a = mergeItems(a, object)
            return array

    try:
        object.serialize()
    except vobject.base.ValidateError:
        try:
            object.n
        except AttributeError:
            print "added n"
            # TODO default name
            #object.n.value = vobject.vcard.Name(family="Nemo")
            object.n.value = vobject.vcard.Name(family="")
        # object.prettyPrint()
        try:
            object.fn
        except AttributeError:
            print "added fn to " + str(object.n)
            object.add("fn")
            # TODO default family name
            #object.fn.value = "Nemo"
            object.fn.value = ""

    # object.prettyPrint()
    array.append(object)

    return array

# merge two items
# we could use fuzzy results to select the %


def mergeItems(one, two):
    print "mergeItems()"
    one.prettyPrint()
    two.prettyPrint()

    # find a smart way to
    # merge two Formatted Name http://tools.ietf.org/html/rfc2426#section-3.1.1
    try:
        if len(two.fn.value) > len(one.fn.value):
            one.add("nickname").value = one.fn.value
            one.fn.value = two.fn.value
    except:
        pass

    # fmerge Name http://tools.ietf.org/html/rfc2426#section-3.1.2
    # this attribute is REQUIRED and can be multi-valued
    try:
        if  (hashName(one) != hashName(two))\
                and (hashName(one) != hashName(two, True)):
            # name is almost the same, use the first one
            one.add("n").value = two.n.value
    except:
        pass

    # join mail address and phone number
    for field in "TEL", "EMAIL":
        ot = getFields(one, field, True)
        tt = getFields(two, field, True)
        nt = filter(lambda x: x not in ot, tt)
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
        print "opts:" + i[0]

    for i in args:
        print "args:" + i

    files = args
    allContacts = []
    for f in files:
        print "file:" + f
        try:
            allContacts = parseVcf(f)
        except IOError:
            print "Error: File not found"
            sys.exit(2)

    myContacts = dedupe(allContacts)
    outfile = open("deduped_addressbook.vcf", "w+")
    print "Creating new addressbook: deduped_addressbook.vcf"
    for i in myContacts:
        # print i.serialize()
        outfile.write(i.serialize())
    print "done"


if __name__ == "__main__":
    main()
