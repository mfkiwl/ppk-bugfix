echo "clean.sh"
rm -rf */__pycache__
pushd ext/rtklib_2.4.3_b34/app/consapp/rnx2rtkp/gcc/
make clean
popd

