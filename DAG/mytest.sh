#!/bin/bash

# declare a name for this job to be sample_job
#PBS -N JOBE
# request 4 processes
#PBS -l nodes=4
# request 4 hours of wall time
#PBS -l walltime=04:00:00
# combine PBS standard output and error files
#PBS -j oe
#PBS -k eo
    
#How many procs do I have?
NN=`cat $PBS_NODEFILE | wc -l`
echo "Processors received = "$NN
echo "script running on host `hostname`"
    
#cd into the directory where I typed qsub
cd $PBS_O_WORKDIR
echo "PBS_NODEFILE"
cat $PBS_NODEFILE
    
#Type in commands to run. Replace a.out with the program name
#to run.
/opt/mpiexec/bin/mpiexec -comm pmi a.out 100 
