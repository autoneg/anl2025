#!/usr/bin/env bash
for notebook in `ls ../notebooks/tutorials/*.ipynb | sort -g` ; do
    jupyter nbconvert --TagRemovePreprocessor.remove_cell_tags='{"remove_cell"}' --to markdown $notebook
    jupyter nbconvert --TagRemovePreprocessor.remove_cell_tags='{"remove_cell"}' --to markdown $notebook
    jupyter nbconvert --TagRemovePreprocessor.remove_cell_tags='{"remove_cell"}' --to markdown $notebook
    jupyter nbconvert --TagRemovePreprocessor.remove_cell_tags='{"remove_cell"}' --to markdown $notebook
done
rm -r docs/tutorials
mkdir docs/tutorials
mv ../notebooks/tutorials/*.md docs/tutorials
cp ./static_tutorials/*.* docs/tutorials
for fils in ../notebooks/tutorials/*_files ; do
    mv $fils docs/tutorials
done
mkdir docs/tutorials/notebooks
for notebook in ../notebooks/tutorials/*.ipynb ; do
    cp $notebook docs/tutorials/notebooks
done

for mdfile in docs/tutorials/*.md; do
    filename1=${mdfile##*/}
    filename=${filename1%???}
    # sed -i='' '/Output()/d' $mdfile
    echo "[Download Notebook](/anl2025/tutorials/notebooks/$filename.ipynb)" >> $mdfile
done
echo "------------------------------------------------"
mkdocs build
# copy images if any to the notebook. This is needed so that we can use images in markdown
for fils in ../notebooks/tutorials/*.ipynb ; do
	orig=`basename ${fils%.*}`
	cp ../notebooks/tutorials/*.jpeg site/tutorials/${orig}/
done
mkdocs gh-deploy
#
# for ext in png jpg gif pdf; do
# 	echo ../notebooks/tutorials/*.$ext ./tutorials/
# 	cp ../notebooks/tutorials/*.$ext ./tutorials/
# 	for fils in tutorials _images ; do
# 		echo ../notebooks/tutorials/*.$ext _build/html/$fils/
# 		cp ../notebooks/tutorials/*.$ext _build/html/$fils/
# 	done
# done
