'''
Scratch50

Downloads Scratch project supplied as argv[1].
'''
import argparse
import json
import os
import re
import requests
import shutil
import urllib
import zipfile

SCRATCH_API_URL = 'http://projects.scratch.mit.edu/internalapi/project/%s/get/'
asset_counter = 0

'''
Zips a folder.
'''
def zipdir(path, ziph):
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))

"""
Takes a dict with nested lists and dicts,
and searches all dicts for a key of the field
provided.
"""
def get_recursively(search_dict, field):
    global asset_counter
    fields_found = []

    for key, value in search_dict.iteritems():

        if key == field:
            if field == 'md5':
                fields_found.append((value, str(asset_counter) + '.' + value.split('.')[-1]))
                search_dict['soundID'] = asset_counter
            elif field == 'baseLayerMD5':
                fields_found.append((value, str(asset_counter) + '.' + value.split('.')[-1]))
                search_dict['baseLayerID'] = asset_counter
            elif field == 'penLayerMD5':
                fields_found.append((value, str(asset_counter) + '.' + value.split('.')[-1]))
                search_dict['penLayerID'] = asset_counter
            elif field == 'objName':
                fields_found.append(search_dict)
            else:
                fields_found.append(value)

            asset_counter += 1

        elif isinstance(value, dict):
            results = get_recursively(value, field)
            for result in results:
                fields_found.append(result)

        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    more_results = get_recursively(item, field)
                    for another_result in more_results:
                        fields_found.append(another_result)

    return fields_found

'''
List flattening method.
'''
def flatten(seq, container=None):
    if container is None:
        container = []
    for s in seq:
        if hasattr(s, '__iter__'):
            flatten(s, container)
        else:
            container.append(s)
    return container 

'''
Count number of lists in a list (blocks).
'''
def count_lists(l):
    total = 0
    for item in l:
        if isinstance(item, list) and item:
            all_lists = True

            for i in item:
                if not isinstance(i, list):
                    all_lists = False
            if all_lists:
                total -= 1

            total += 1
            total += count_lists(item)

        # account for functions with > 2 arguments
        if item == 'procDef':
            params = l[2]
            if len(params) > 1:
                total += len(params) - 1
            if len(params) == 0:
                total += 1
    return total

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download a Scratch project!')

    parser.add_argument('-d', help='URL of project to download')
    parser.add_argument('-o', help='local path of project file (sb2) to open and parse')

    args = parser.parse_args()

    if not args.d and not args.o:
        print 'Must include either a download link (-d) or local path (-o) to run script!'
        exit()

    # download and assemble SB2
    if args.d:
        # grab the project ID from the scratch URL
        m = re.search(r'[0-9]+', args.d)
        project_id = m.group(0)

        # download project JSON
        r = requests.get(SCRATCH_API_URL % project_id)

        if r.status_code >= 300:
            print 'Error retrieving JSON; %s' % r.status_code
            exit()

        if not os.path.exists(project_id):
            os.makedirs(project_id)

        old_project = False

        try:
            with open(os.path.join(project_id, project_id + '.json'), 'w') as f:
                json.dump(r.json(), f)
        except:
            os.remove(os.path.join(project_id, project_id + '.json'))
            old_project = True
            url = SCRATCH_API_URL % project_id
            testfile = urllib.URLopener()
            testfile.retrieve(url, project_id + '.sb2')

        # only manually assemble the project if it's a newer project (saved in JSON)
        if not old_project:
            with open(os.path.join(project_id, project_id + '.json'), 'r') as f:
                j = json.load(f)

                # obtain all of the asset links by their md5 identifiers in the JSON
                md5s = get_recursively(j, 'md5')
                md5s2 = get_recursively(j, 'baseLayerMD5')
                md5s3 = get_recursively(j, 'penLayerMD5')

                total_files = md5s + md5s2 + md5s3

                # download each asset
                for item in total_files:
                    url = 'http://cdn.assets.scratch.mit.edu/internalapi/asset/%s/get/' % item[0] 
                    testfile = urllib.URLopener()
                    testfile.retrieve(url, os.path.join(project_id, item[1]))

            with open(os.path.join(project_id, project_id + '.json'), 'w') as f:
                json.dump(j, f)

            # zip folder as an SB2 file
            zipf = zipfile.ZipFile(project_id + '.sb2', 'w', zipfile.ZIP_DEFLATED)
            zipdir(project_id, zipf)
            zipf.close()

        # remove scratch assembly folder
        shutil.rmtree(project_id)

    # open and parse SB2
    if args.o:
        project_id = args.o.split('.')[0]
        path = args.o
        folder_path = path.split('.')[0]

        # unzip SB2 to get access to JSON
        zip_ref = zipfile.ZipFile(path, 'r')
        if len(zip_ref.namelist()) > 1:
            zip_ref.extractall(folder_path)
        else:
            zip_ref.extractall('.')
        zip_ref.close()

        if len(os.listdir(folder_path)) == 1:
            folder_path = os.path.join(folder_path, os.listdir(folder_path)[0])

        # find the JSON file in the folder
        for item in os.listdir(folder_path):
            if item.endswith('.json'):
                with open(os.path.join(folder_path, item), 'r') as f:
                    j = json.load(f)

                    # json we will be outputting
                    return_j = {
                        'num_sprites': None,
                        'sprites': [],
                    }

                    # number of sprites
                    num_sprites = get_recursively(j, 'info')[0]['spriteCount']
                    return_j['num_sprites'] = num_sprites

                    # number of scripts per sprite
                    sprites = get_recursively(j, 'objName')

                    # add a sprite and a list of scripts for it for each entry in json
                    for index1, sprite in enumerate(sprites):
                        num_scripts = None

                        if 'scripts' in sprite:
                            num_scripts = len(sprite['scripts'])
                        else:
                            num_scripts = 0

                        if 'sounds' in sprite:
                            num_sounds = len(sprite['sounds'])
                        else:
                            num_sounds = 0

                        return_j['sprites'].append({
                            'name': sprite['objName'],
                            'num_scripts': num_scripts,
                            'num_sounds': num_sounds,
                            'scripts': [],
                        })

                        if num_scripts > 0:
                            for index2, script in enumerate(sprite['scripts']):
                                flat_script = flatten(script)
                                num_conditions = flat_script.count('doIf') + flat_script.count('doIfElse')

                                num_loops = flat_script.count('doRepeat') + flat_script.count('doForever') + flat_script.count('doUntil') + flat_script.count('doWaitUntil')
                                num_blocks = count_lists(script[2])

                                return_j['sprites'][index1]['scripts'].append({
                                    'num_conditions': num_conditions,
                                    'num_loops': num_loops,
                                    'num_blocks': num_blocks
                                })

                    # number of variables per script
                    variables = get_recursively(j, 'variables')

                    if not variables:
                        return_j['variables'] = 0
                    else:
                        return_j['variables'] = len(variables[0])

                    print json.dumps(return_j, indent=4, sort_keys=True)

        # remove scratch assembly folder
        shutil.rmtree(project_id)
