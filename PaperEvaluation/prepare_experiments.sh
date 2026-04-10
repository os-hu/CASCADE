
echo "build CASCADE venv"

python3 -m venv cascade.venv

# install it:

./cascade.venv/bin/pip install ./CASCADE



echo "build DocChecker venv"

python3 -m venv envDocChecker
./envDocChecker/bin/pip install torch transformers gdown codetext tree_sitter_languages tree_sitter==0.20.4

   
echo "build C4RLLaMA venv"

python3 -m venv envC4RLLaMA
./envC4RLLaMA/bin/pip install -r ./drivers/C4RLLaMA/requirments.txt

echo "you have to download the retrained DocChecker model https://figshare.com/s/981c2fbe830b905b01a9 and put it in /drivers/DocChecker/pretrained_model"
echo "you have to download the retrained C4RLLaMA weights https://figshare.com/s/812541da6a1f33025f69 and put them in /drivers/C4RLLaMA/weights"
