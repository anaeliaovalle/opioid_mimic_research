#!/usr/bin/python

#--------------------------------
# Written by Marzyeh Ghassemi, CSAIL, MIT
# Sept 21, 2012
# Updated for Python 3, added Notebook, db connection
# by Tom J. Pollard 13 Nov, 2017
# Please contact the author with errors found.
# mghassem {AT} mit {DOT} edu
#--------------------------------

import os
import os.path
import re
import sys
import time
from collections import OrderedDict


def addToDrugsFound(line, drugFlagArr, genericToBrandDrugMap, genericDrugToIndex):
    """
    ###### function addToDrugs
    #   line:    line of text to search
    #   drugs:   flag array to modify
    #   genericToBrandDrugMap: list of search terms in (generic:search list) form
    #   genList: list of all generic keys being searched for
    #
    #   Searches the provided line for drugs that are listed. Inserts
    #   a 1 in the drugs array provided at the location which maps
    #   the found key to the generics list
    """
    for (generic, names) in genericToBrandDrugMap.items():
        if re.search(names, line, re.I):
            flagIndex= genericDrugToIndex[generic]
            drugFlagArr[flagIndex] = 1
    return drugFlagArr


def readAndParseDrugList(DRUGLIST_FILE):
    """
    ###### function readDrugs
    #   f:       file
    #   genList: list of search terms in (generic:search list) form
    #
    #   Converts lines of the form "generic|brand1|brand2" to a
    #   dictionary keyed by "generic" with value "generic|brand1|brand2
    #   and uses an ordered dict to preserve order of drug names
    """
    with open(DRUGLIST_FILE) as f:
        print("Using drugs from {}".format(DRUGLIST_FILE))
        lines = f.read()
        drugGenerics = re.findall("^(.*?)\|", lines, re.MULTILINE)
        drugGenerics = [x.lower() for x in drugGenerics]
        drugBrandsWithGeneric = lines.split("\n")
        drugBrandsWithGeneric = [x.lower() for x in drugBrandsWithGeneric]

    return OrderedDict(zip(drugGenerics, drugBrandsWithGeneric))


def search(NOTES,
           DRUGLIST_FILE,
           SUMMARY_FILE = "output.csv",
           VERBOSE = False):
    """
    ###### Search the notes
    # NOTES: dataframe loaded from the noteevents table
    # DRUG_FILE: list of drugList drugs to search for
    #
    # NB: files should have a line for each distinct drug type,
    #      and drugs should be separated by a vertical bar '|'
    #
    # LIMIT FOR PARSING: max number of notes to search.
    # OUTPUT: name of the output file.
    """

    if os.path.isfile(SUMMARY_FILE):
        print('The output file already exists.\n\nRemove the following file or save with a different filename:')
        print(os.path.join(os.getcwd(), SUMMARY_FILE))
        return

    starttime = time.time()

    # Get the drugs into a structure we can create flags from
    genericToBrandDrugMap = readAndParseDrugList(DRUGLIST_FILE=DRUGLIST_FILE)
    genericDrugList = genericToBrandDrugMap.keys()
    genericDrugToIndex = dict((v, k) for k, v in enumerate(genericToBrandDrugMap.keys()))

    # # Create indices for the flat list
    # # This allows us to understand which "types" are being used
    # lengths = [len(type) for type in genericDrugList]
    # prevLeng = 0
    # starts = []
    # ends = []
    # for leng in lengths:
    #     starts.append(prevLeng)
    #     ends.append(prevLeng + leng - 1)
    #     prevLeng = prevLeng + leng

    # Write heads and notes to new doc
    with open(SUMMARY_FILE, 'a') as f_out:
        header = '"row_id","subject_id","hadm_id","hist_found","opiate_history",' \
                 '"admit_found","dis_found","group","opiates","'\
                 + '","'.join(genericDrugList) + '"\n'
        f_out.write(header)

        # Parse each patient record
        print("Reading documents...")

        for note in NOTES.itertuples():
            if note.Index % 100 == 0:
                print("...index: {}. row_id: {}. subject_id: {}. hadm_id: {}. \n".format(note.Index, note.row_id, note.subject_id, note.hadm_id))
                sys.stdout.flush()

            # Reset some per-patient variables
            section = ""
            newSection = ""
            admitFound = 0  # admission note found
            dischargeFound = 0  # discharge summary found
            histFound = 0  # medical history found
            opiateHist = 0
            drugsAdmit = [0]*len(genericDrugList)  # extend list to number of drugs
            drugsDis = [0]*len(genericDrugList)

            # Read through lines sequentially
            # If this looks like a section header, start looking for drugs
            for line in note.text.split("\n"):

                # Searches for a section header based on heuristics
                m = re.search("""^((\d|[A-Z])(\.|\)))?\s*([a-zA-Z',\.\-\*\d\[\]\(\) ]+)(:| WERE | IS | ARE |INCLUDED|INCLUDING)""", line, re.I)
                if m:
                    newSection = ""
                    # Past Medical History Section
                    if re.search('med(ical)?\s+hist(ory)?', line, re.I):
                        newSection = "hist"
                        histFound = 1

                    # Discharge Medication Section
                    elif re.search('medication|meds', line, re.I) and re.search('disch(arge)?', line, re.I):
                        newSection = "discharge"
                        dischargeFound = 1

                    # Admitting Medication Section
                    elif re.search('admission|admitting|home|nh|nmeds|pre(\-|\s)?(hosp|op)|current|previous|outpatient|outpt|outside|^[^a-zA-Z]*med(ication)?(s)?', line, re.I) \
                    and (section == "admit" or re.search('medication|meds', line, re.I)):
                        newSection = "admit"
                        admitFound = 1

                    # Med section ended, now in non-meds section
                    if section != newSection:
                        section = newSection

                # If in history section, search for opiates
                if 'hist' in section:
                    if re.search('opiate(s)?', line, re.I):
                        opiateHist = 1

                # If in meds section, look at each line for specific drugs
                elif 'admit' in section:
                    drugsAdmit = addToDrugsFound(line, drugsAdmit, genericToBrandDrugMap, genericDrugToIndex)

                # Already in meds section, look at each line for specific drugs
                elif 'discharge' in section:
                    drugsDis = addToDrugsFound(line, drugsDis, genericToBrandDrugMap, genericDrugToIndex)

                # A line with information which we are uncertain about...
                elif re.search('medication|meds', line, re.I) and re.search('admission|discharge|transfer', line, re.I):
                    if VERBOSE:
                        print('?? {}'.format(line))
                    pass

            hasDischarge = dischargeFound == 1
            hasDrugsInDischarge = 1 in drugsDis
            hasAdmit = admitFound == 1
            hasDrugsInAdmit = 1 in drugsAdmit

            group = 0
            # Group 0: Patient has no medications on admission section (or no targeted meds)
            #          and medications on discharge from the list
            if hasDischarge and hasDrugsInDischarge and (not hasAdmit or not hasDrugsInAdmit):
                group = 0

            # Group 1: Patient has a medications on admission section with no targeted meds
            #          and no medications on discharge
            elif hasAdmit and not hasDrugsInAdmit and not hasDischarge:
                group = 1

            # Group 2: Patient has medications on admission section, but none from the list
            #          and no medications on discharge from the list
            elif hasAdmit and not hasDrugsInAdmit and hasDischarge and not hasDrugsInDischarge:
                group = 2

            # Group 3: Patient has medications on admission (at least one from the list)
            elif hasDrugsInAdmit:
                group = 3

            else:
                if VERBOSE:
                    print('Uncertain about group type for row_id = {}'.format(note.row_id))
                pass

            if VERBOSE:
                print('group is {}'.format(group))

            # Combine the admit and discharge drugs lists
            member = int(hasDrugsInAdmit)

            # save items to csv
            f_out.write(str(note.row_id) + "," + str(note.subject_id) + "," + str(note.hadm_id) + "," + str(histFound)
                        + "," + str(opiateHist) + "," + str(admitFound) + "," + str(dischargeFound)  + "," + str(group)
                        + "," + str(member) + "," + ",".join(map(str, drugsAdmit)) + "\n")

    # Print summary of analysis
    stoptime = time.time()
    print("Done analyzing {} documents in {} seconds ({} docs/sec)".format(len(NOTES),
        round(stoptime - starttime, 2), round(len(NOTES) / (stoptime - starttime), 2)))
    print("Summary file is in {}".format(os.getcwd()))
