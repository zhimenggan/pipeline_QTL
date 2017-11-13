'''
|project_name|
===================

:Author: |author_name|
:Release: |version|
:Date: |today|


Overview
========

|long_description|


Purpose
=======


Ruffus pipeline which runs quantitative trait analysis.

Originally thought for human QTls on gene expression but depending on the tool
can run on other quantitative molecular phenotypes.


Usage and options
=================

These are based on CGATPipelines_ and Ruffus_, not docopt.

.. _CGATPipelines: https://github.com/CGATOxford/CGATPipelines

.. _Ruffus: http://www.ruffus.org.uk/


For command line help type:

    python pipeline_QTL.py --help


Configuration
=============

This pipeline is built using a Ruffus/CGAT approach. You need to have Python,
Ruffus, CGAT core tools and any other specific dependencies needed for this
script.

A configuration file was created at the same time as this script.

Use this to extract any arbitrary parameters that could be changed in future
re-runs of the pipeline.


Input files
===========

At least correctly formatted files with genotype and phenotype data.

Depending on the tool run covariate files, SNP position and probe position
files can be added.


Quality controlled (molecular) phenotype (e.g. gene expression) and genotyping data. 

Optionally covariates and error covariance matrix.

Annotation files are also needed for cis vs trans analysis (SNPs positions and probe positions and any associated annotations).

Files need to be in the same format as MatrixEQTL requires:

SNPs/genes/covariates in rows, individuals in columns with (dummy) headers and row names (the first column and first row are skipped when read).

Missing values must be set as "NA".

SNP and probe position files, e.g.
   - snp146Common_MatrixEQTL_snp_pos.txt
   - biomart_QCd_probes_genomic_locations_annot_MatrixeQTL.txt
must be tab separated.

See:

http://www.bios.unc.edu/research/genomic_software/Matrix_eQTL/


Naming convention for input files
=================================

Output files get named based on the input files. The script assumes "cohort" is the same for input files (but only takes it from the genotype file).

Please rename your files in the following way (use soft links to rename for example):

Infile: cohort-platform-other_descriptor.suffix

Outfile: cohort-platform_infile1-descriptor1-platform_infile2-descriptor2.new_suffix

For example:

genotype file: airwave-illumina_exome-all_chrs.geno

phenotype file: airwave-NMR-blood.txt

and depending on the input and arguments you might get:

airwave-illumina_exome-all_chrs-NMR-blood.MxEQTL
airwave-illumina_exome-all_chrs-NMR-blood.MxEQTL.cis
airwave-illumina_exome-all_chrs-NMR-blood.MxEQTL.trans
airwave-illumina_exome-all_chrs-NMR-blood.MxEQTL.qqplot.svg
airwave-illumina_exome-all_chrs-NMR-blood.MxEQTL.degrees_condition.txt
airwave-illumina_exome-all_chrs-NMR-blood.MxEQTL.log

File names can get long so use abbreviations or short versions.

You can also override this and simply choose your outfile prefix.

If you do not use an outfile name and your files do not follow the naming above you might get something like:

"SNP.txt-NA-NA-NA-NA.MxEQTL"



Pipeline output
===============

Namely a qqlot and tables of genotype molecular phenotype associations. These are saved in the working directory.


Requirements
============

See requirements.txt and Dockerfile for information

Minimum requirements are:

* Ruffus
* CGATCore
* R >= 3.2
* Python >= 3.5
* r-docopt
* r-data.table
* r-ggplot2


Documentation
=============

    For more information see:

        |url|

'''
################
# Get modules needed:
import sys
import os
import re
import subprocess

# Pipeline:
from ruffus import *

# Database:
import sqlite3

# Try getting CGAT: 
try:
    import CGAT.IOTools as IOTools
    import CGATPipelines.Pipeline as P
    import CGAT.Experiment as E

except ImportError:
    print('\n', "Warning: Couldn't import CGAT modules, these are required. Exiting...")
    raise

# required to make iteritems python2 and python3 compatible
from builtins import dict

# Import this project's module, uncomment if building something more elaborate: 
#try: 
#    import module_template.py 

#except ImportError: 
#    print("Could not import this project's module, exiting") 
#    raise 

# Import additional packages: 
# Set path if necessary:
#os.system('''export PATH="~/xxxx/xxxx:$PATH"''')
################


################
# Load options from the config file
# Pipeline configuration
ini_paths = [os.path.abspath(os.path.dirname(sys.argv[0])),
             "../",
             os.getcwd(),
             ]

def getParamsFiles(paths = ini_paths):
    '''
    Search for python ini files in given paths, append files with full
    paths for P.getParameters() to read.
    Current paths given are:
    where this code is executing, one up, current directory
    '''
    p_params_files = []
    for path in ini_paths:
        for f in os.listdir(os.path.abspath(path)):
            ini_file = re.search(r'pipelin(.*).ini', f)
            if ini_file:
                ini_file = os.path.join(os.path.abspath(path), ini_file.group())
                p_params_files.append(ini_file)
    return(p_params_files)

P.getParameters(getParamsFiles())

PARAMS = P.PARAMS
# Print the options loaded from ini files and possibly a .cgat file:
#pprint.pprint(PARAMS)
# From the command line:
#python ../code/pq_example/pipeline_pq_example/pipeline_pq_example.py printconfig


# Set global parameters here, obtained from the ini file
# e.g. get the cmd tools to run if specified:
#cmd_tools = P.asList(PARAMS["cmd_tools_to_run"])

def get_py_exec():
    '''
    Look for the python executable. This is only in case of running on a Mac
    which needs pythonw for matplotlib for instance.
    '''
    try:
        PARAMS["py_exec"]
        py_exec = '{}'.format(PARAMS['py_exec'])
    except NameError:
        E.warn('''
               You need to specify the python executable, just "python" or
               "pythonw" is needed. Trying to guess now...
               ''')
    else:
        test_cmd = subprocess.check_output(['which', 'pythonw'])
        sys_return = re.search(r'(.*)pythonw', str(test_cmd))
        if sys_return:
            py_exec = 'pythonw'
        else:
            py_exec = 'python'
    return(py_exec)

def getINIpaths():
    '''
    Get the path to scripts for this project, e.g.
    project_xxxx/code/project_xxxx/:
    e.g. my_cmd = "%(scripts_dir)s/bam2bam.py" % P.getParams()
    '''
    try:
        project_scripts_dir = '{}/'.format(PARAMS['project_scripts_dir'])
        E.info('''
               Location set for the projects scripts is:
               {}
               '''.format(project_scripts_dir)
               )
    except KeyError:
        E.warn('''
               Could not set project scripts location, this needs to be
               specified in the project ini file.
               ''')
        raise

    return(project_scripts_dir)
################


################
# Get pipeline.ini file
# Use this if not based on CGATPipelines:
# Many more functions need changing though

#def getINI():
#    path = os.path.splitext(__file__)[0]
#    paths = [path, os.path.join(os.getcwd(), '..'), os.getcwd()]
#    f_count = 0
#    for path in paths:
#        if os.path.exists(path):
#            for f in os.listdir(path):
#                if (f.endswith('.ini') and f.startswith('pipeline')):
#                    f_count += 1
#                    INI_file = f

#    if f_count != 1:
#        raise ValueError('''No pipeline ini file found or more than one in the
#                            directories:
#                            {}
#                        '''.format(paths)
#                        )
#    return(INI_file)

# With CGAT tools run as:
# Load options from the config file
#INI_file = getINI()
#PARAMS = P.getParameters([INI_file])

# Read from the pipeline.ini configuration file
# where "pipeline" = section (or key)
# "outfile_pandas" option (value)
# separated by "_"
# CGATPipelines.Pipeline takes some of the work away.
# e.g.:
'''
def someFunc():
    " Comment function "
    if "pipeline_outfile_pandas" in PARAMS:
        outfile = PARAMS["pipeline_outfile_pandas"]
    else:
        outfile = 'pandas_DF'

    statement = " cd pq_results ; python pq_example.py --createDF -O %(outfile)s "
    # Use CGATPipelines to handle the job:
    P.run()
'''
################


################
# Utility functions
def connect():
    '''utility function to connect to database.

    Use this method to connect to the pipeline database.
    Additional databases can be attached here as well.

    Returns an sqlite3 database handle.
    '''

    dbh = sqlite3.connect(PARAMS["database_name"])
    statement = '''ATTACH DATABASE '%s' as annotations''' % (
        PARAMS["annotations_database"])
    cc = dbh.cursor()
    cc.execute(statement)
    cc.close()

    return dbh
################


################
# Specific pipeline tasks
# Tools called need the full path or be directly callable

@mkdir('MatrixEQTL')
@transform()
def run_MxQTL():
    '''

    '''

    statement = '''
                
                '''
    P.run()

def load_MxQTL():
    '''
    Load the results of run_MxQTL() into an SQL database.
    '''
    P.load(infile, outfile, '--add-index=word')

@transform((INI_file, "conf.py"),
           regex("(.*)\.(.*)"),
           r"\1.counts")
def countWords(infile, outfile):
    '''count the number of words in the pipeline configuration files.'''

    # the command line statement we want to execute
    statement = '''awk 'BEGIN { printf("word\\tfreq\\n"); }
    {for (i = 1; i <= NF; i++) freq[$i]++}
    END { for (word in freq) printf "%%s\\t%%d\\n", word, freq[word] }'
    < %(infile)s > %(outfile)s'''

    # execute command in variable statement.
    #
    # The command will be sent to the cluster.  The statement will be
    # interpolated with any options that are defined in in the
    # configuration files or variable that are declared in the calling
    # function.  For example, %(infile)s will we substituted with the
    # contents of the variable "infile".
    P.run()


@transform(countWords,
           suffix(".counts"),
           "_counts.load")
def loadWordCounts(infile, outfile):
    '''load results of word counting into database.'''
    P.load(infile, outfile, "--add-index=word")
################

################
# Copy to log enviroment from conda:
# TO DO: add to pipeline.py
def conda_info():
    '''
    Print to screen conda information and packages installed.
    '''

    statement = '''conda info -a ;
                   conda list -e > conda_packages.txt ;
                   conda list --show-channel-urls ;
                   conda env export > environment.yml
                '''
    P.run()

################

################
# Create the "full" pipeline target to run all functions specified
@follows(loadWordCounts, conda_info)
def full():
    pass
################


################
# Specify function to create reports pre-configured with sphinx-quickstart: 
def make_report():
    ''' Generates html and pdf versions of restructuredText files
        using sphinx-quickstart pre-configured files (conf.py and Makefile).
        Pre-configured files need to be in a pre-existing report directory.
        Existing reports are overwritten.
    '''
    if os.path.exists('report'):
        statement = ''' cd report ;
                        checkpoint ;
                        make html ;
                        ln -s _build/html/index.hmtl . ;
                        checkpoint ;
                        make latexpdf ;
                        ln -s _build/latex/pq_example.pdf .
                    '''
        E.info("Building pdf and html versions of your rst files.")
        P.run()

    else:
        E.stop(''' The directory "report" does not exist. Did you run the config
                   option? This should copy across templates for easier
                   reporting of your pipeline.
                   If you changed the dir names, just go in and run "make html" or
                   "make latexpdf" or follow Sphinx docs.
                ''')

    return
################


################
if __name__ == "__main__":
    sys.exit(P.main(sys.argv))
################
