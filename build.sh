echo "build.sh"
pushd ext/rtklib_2.4.3_b34/app/consapp/rnx2rtkp/gcc/
make
popd
echo "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
echo "To prepare python library, please run"
echo ""
echo "$ python -m pip install -r requirementx.txt"
echo ""
echo "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
