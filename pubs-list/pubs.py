import sys
import argparse
sys.path.append('../../../software/pylatexenc-master')
from pylatexenc.latex2text import LatexNodes2Text
import re


CONF_BIB_FILE = 'my-pubs.bib'
JOURNAL_BIB_FILE = 'my-journal-pubs.bib'
REQUIRED_BIBTEX_FIELDS = ['ID', 'ENTRYTYPE', 'title', 'author', 'year', 'month', 'url', 'booktitle']
OPTIONAL_BIBTEX_FIELDS = ['journal', 'shortid']
BIBTEX_FIELDS = REQUIRED_BIBTEX_FIELDS + OPTIONAL_BIBTEX_FIELDS

def month_to_num(mon):
    month_num = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
    if mon in month_num:
        return month_num[mon]
    else:
        return 0

def replace_accents(s):
    accents = {"\\'o": 'ó', '\\^{\\i}': 'î', '\\aa': 'å', '\\r a': 'å', '\\r{a}': 'å'}
    for a,b in accents.items():
        s = s.replace(a, b)
    return s

def format_authors(authors, remove_self=False):
    if len(authors) == 0:
        return ''
    res = ''
    if remove_self:
        authors.remove('Peter Scholl')
        if len(authors) == 0:
            return ''
        res += 'with '
        if len(authors) == 1:
            res += authors[0]
        elif len(authors) == 2:
            res += f"{authors[0]} and {authors[1]}"
        else:
            for author in authors[:-1]:
                res += f"{author}, "
            res += f"and {authors[-1]}"
    else:
        if len(authors) == 1:
            res = authors[0]
        elif len(authors) == 2:
            res = f"{authors[0]} and {authors[1]}"
        else:
            res = ", ".join(authors[:-1]) + f", and {authors[-1]}"
    return res

def parse_bib(f, strip_latex_formatting=True, remove_self=False):
    with open(f) as bib_file:
        import bibtexparser
        bib_db = bibtexparser.load(bib_file)

    print('Generating bibtex index...', file=sys.stderr)
    records = []    
    temp_bib = bibtexparser.bibdatabase.BibDatabase()

    for entry in bib_db.entries:
        formatted_entry = {}
        # store original bibtex in case we need it
        temp_bib.entries = [entry]
        formatted_entry['bibtex'] = bibtexparser.dumps(temp_bib)
        
        for key in BIBTEX_FIELDS:
            # remove '{}', replace '\n' with ' ' and convert to unicode
            # also strip out leading '\url' for note field
            if key in entry:
                if strip_latex_formatting:
                    latex = replace_accents(entry[key])
                    # converter.decode_Tex_Accents(entry[key], utf8_or_ascii=1) # replacing accents by UTF8
                    #latex = entry[key] \
                    latex = latex.translate({ord(c): v for (c,v) in [('\n', ' '), ('{', None), ('}', None), ('~', ' ')]}) \
                        .lstrip('\\url')
                    latex = LatexNodes2Text().latex_to_text(latex)
                else:
                    latex = entry[key]
                # Parse author list
                if key == 'author':
                    authors = [a.strip() for a in re.split(r'\s+and\s+', latex)]
                    # Convert "Surname, Firstname" to "Firstname Surname"
                    for i, author in enumerate(authors):
                        if ', ' in author:
                            surname, firstname = author.split(', ', 1)
                            authors[i] = f"{firstname} {surname}"
                    # Join authors with proper formatting
                    latex = format_authors(authors, remove_self)
            else:
                latex = ''
                if key in REQUIRED_BIBTEX_FIELDS:
                    print('*WARNING* Missing key "%s" in "%s"' % (key, entry['ID']), file=sys.stderr)
            formatted_entry[key] = latex
            #formatted_entry[key] = unicode(entry[key]).translate({ord(c): v for (c,v) in
            #            [('\n', unicode(' ')), ('{', None), ('}', None)]}).lstrip('\\url')
        records.append(formatted_entry)
    
    records.sort(key=lambda x: month_to_num(str(x['month'][:3])), reverse=True)
    records.sort(key=lambda x: x['year'], reverse=True)
    return records

def gen_html(records, separate_by_year, eprint_records=False):
    records = [r for r in records if (r['ENTRYTYPE'] == 'misc') == eprint_records]

    year = records[0]['year']

    res = ""
    if separate_by_year:
        res += f"""
<h3>{year}</h3>
"""
    res += '<ol class="begin">\n'
    
    for record in records:
        #if record['ENTRYTYPE'] == 'misc':
        #    if not eprint_records:
        #        continue
        #elif eprint_records:
        #    continue
            
        if record['shortid'] != '':
            id = ' id=\"%s\"' % record['shortid']
        else:
            id = ''
        
        eprint = ''
        if eprint_records and record['booktitle'] == '':
            # append year to misc records without a separate title
            eprint = '(<a href="' + record['url'] + '">eprint</a>, ' + str(record['year']) + ')<br />\n'
        elif record['url'] == 'https://eprint.iacr.org/' or record['url'] == 'coming soon':
            eprint = ''
        elif record['url'] == 'https://faest.info':
            eprint += '(<a href="' + record['url'] + '">website</a>)'
        elif 'eprint.iacr.org' in record['url']:
            eprint += '(<a href="' + record['url'] + '">eprint</a>)'
        elif 'doi.org' in record['url']:
            eprint += '(<a href="' + record['url'] + '">eprint</a>)'
        elif 'arxiv.org' in record['url']:
            eprint += '(<a href="' + record['url'] + '">arXiv</a>)'
        elif 'slides' in record['url']:
            eprint += '(<a href="' + record['url'] + '">slides</a>)'
        else:
            raise ValueError(f"Unknown URL type for entry {record['ID']}: {record['url']}")
        
        if separate_by_year and year != record['year']:
            year = record['year']
            res += u'\n</ol>\n\n<h3>%s</h3>\n\n<ol class="begin">\n' % year
        
        # fix titles with math
        if record['title'].startswith('SPD'):
            # fix SPDZ2k title
            record['title'] = 'SPDZ2k: Efficient MPC mod 2^k for Dishonest Majority'
        if record['title'].startswith('Moz'):
            record['title'] = 'Moz{Z_2^k}arella: Efficient Vector-OLE and Zero-Knowledge Proofs Over Z_2^k'
        if record['title'].startswith('Low-Complexity Weak Pseudorandom'):
            record['title'] = 'Low-Complexity Weak Pseudorandom Functions in AC0[MOD2]'
        
        res += f"""
<li{id}>
<strong>{record['title']}</strong><br />
<em>{record['author']}</em><br />
"""
        if record['booktitle'] != '':
            res += f"<em>{record['booktitle']}</em><br />\n"
        elif record['journal'] != '':
            res += f"<em>{record['journal']}, {record['year']}</em><br />\n"
        res += f"""
{eprint}
</li>
"""
    res += '</ol>\n'
    return res

def gen_latex_cite(records):
    print('\\cite{')
    for record in records:
        print(record['ID'] + ', ', sep='')
    print('}')

def gen_latex_list(records, exclude_me=True, journals=False, add_urls=False):
    """ Print nicely formatted itemized records """
    res = ''
    for record in records:
        res += '    \\item \\textbf{'

        title = record['title']
        if add_urls and record['url'] and record['url'] not in ['coming soon', 'https://eprint.iacr.org/']:
            title = f"\\href{{{record['url']}}}{{{title}}}"
        res += title + '}'
        authors = [x.strip() for x in re.split(r'\sand\s', record['author'])]
        #authors = [x.strip() for x in record['author'].split(' and ')]
        has_coauthors = len(authors) > 1 or record['author'].startswith('with ')
        if has_coauthors:
            res += ' --- '
        # if exclude_me:
        #     if 'Peter Scholl' in authors:
        #         authors.remove('Peter Scholl')
        #     else:
        #         print(f'***** {authors}')
        #     if not single_author:
        #         res += 'with '
        for author in authors[:-2]:
            res += author + ', '
        if len(authors) == 1:
            res += authors[0]
        elif len(authors) >= 2:
            res += authors[-2] + ' and ' + authors[-1]

        res += ' (\\emph{'
        if journals:
            res += record['journal'] + ', ' + record['year']
        else:
            res += record['booktitle']
        res += '})\n'
        #if year != record['year']:
        #    year = record['year']
        #    res += u'\n</ol>\n\n<h3>%s</h3>\n\n<ol class="continue">\n' % year
        #if record['title'].startswith('SPD'):
        #    # fix SPDZ2k title
        #    record['title'] = 'SPDZ2k: Efficient MPC mod 2^k for Dishonest Majority'
        #res += u"""
    return res


def print_html(f, separate_by_year, eprint_records):
    records = parse_bib(f)
    #for record in records:
    #    print(record['title'])

    html = gen_html(records, separate_by_year, eprint_records=eprint_records)
    #print(html)
    #spcial_char_map = {ord('\xc2\xa0'):'ae', ord('ü'):'ue', ord('ö'):'oe', ord('ß'):'ss'}

    uni = html.encode('utf-8')
    #uni = uni.replace("\xc2\xa0", " ")
    #uni = uni.replace("\n", u"\n")
    print(html)

if __name__ == '__main__':
    # todo
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--eprint', help="Eprint entries only (of 'misc' type)",
                    action="store_true", default=False)
    #parser.add_argument("-c", "--conf", help="Include conference articles (labelled @inproceedings)",
    #                action="store_true", default=True)
    parser.add_argument("-j", "--journal", help="Parse journal bibtex file",
                    action="store_true", default=False)
    parser.add_argument("-l", "--latex", help="Output latex code instead of HTML",
                    action="store_true", default=False)
    parser.add_argument("--url", help="Add hyperlinks to publications with URLs (LaTeX output only)",
                    action="store_true", default=False)
    args = parser.parse_args()

    #included_categories = {}
    #included_categories['eprint'] = args.eprint
    #included_categories['conf'] = args.conf
    #included_categories['journal'] = args.journal
    # {'conf': True, 'journal': False, 'eprint': False}

    if args.journal:
        f = JOURNAL_BIB_FILE
        separate_by_year = False
    else:
        f = CONF_BIB_FILE
        separate_by_year = True
    
    eprint_records = args.eprint
    if eprint_records:
        separate_by_year = False
        

    if args.latex:
        # For Latex code
        bib_records = parse_bib(f, strip_latex_formatting=False, remove_self=True)
        latex = gen_latex_list(bib_records, journals=False, add_urls=args.url)
        print(latex)
    else:
        # For HTML code
        print_html(f, separate_by_year, eprint_records)

    #gen_latex_cite()