NAME=ppk_camera_geotagging


.PHONY: build
build:
	@echo build
	. build.sh
test:
	@echo test
	python3 ppk_camera_geotagging.py \
	    sample/100_0067_Rinex.obs sample/02250780.20o sample/02250780.20n sample/100_0067_Timestamp.MRK \
	    35.657204659,140.048099674,43.7597 \
		--rtklib_template_file=./conf/template-rnx2rtkp-conf.txt \
		--photo_file_prefix=100_0067_
clean:
	@echo clean
	. clean.sh
tar: clean
	tar cfvz ppk_camera_geotagging_`date "+%Y%m%d-%H%M%S"`.tar.gz 00README.md Makefile build.sh clean.sh conf/ ext/ ppk_camera_geotagging.py sample/ xgnss/


