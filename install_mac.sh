TMP_DIR="$(mktemp -d)"
#make sure running with superuser privileges
if [ "$(id -u)" != "0" ]; then
    echo "Please run with sudo."
    exit 1
fi

install_path="/Library/Application Support/DeepMake"
conda_install_path="~/miniconda3"
aeplugin_path="/Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore/"

mkdir -p $install_path

if command -v conda &> /dev/null; then
    echo "conda is installed and available in the PATH"
    conda_path="conda"
else
    conda_path=$conda_install_path"/bin/conda"
    echo "conda is not installed or not in the PATH"
    curl -s https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh -o $TMP_DIR/miniconda.sh
    bash $TMP_DIR/miniconda.sh -b -p $conda_install_path
    $conda_path init zsh bash
    $conda_path config --set auto_activate_base false
fi

#Install git from conda if not installe
if ! command -v git &> /dev/null; then
    $conda_path install -y git
fi

#if install path is empty, clone the repo otherwise pull the latest changes
if [ -z "$(ls -A $install_path)" ]; then
    echo "Installing DeepMake to $install_path"
    git clone https://github.com/DeepMakeStudio/DeepMake.git $install_path
else
    echo "Updating DeepMake at $install_path"
    cd $install_path
    git pull
    cd -
fi

$conda_path env create -y -f $install_path/environment.yml

#Download binaries
curl -s -L https://github.com/DeepMakeStudio/DeepMake/releases/latest/download/Binaries_Mac.zip -o "$TMP_DIR"/Binaries_Mac.zip


unzip -o "$TMP_DIR"/Binaries_Mac.zip -d "$TMP_DIR"
cp -Rf "$TMP_DIR"/DeepMake/DeepMake_ae.bundle "$aeplugin_path"
cp -Rf "$TMP_DIR"/DeepMake/appPrompt.app /Applications/

rm -Rf $TMP_DIR

echo "Installation complete."