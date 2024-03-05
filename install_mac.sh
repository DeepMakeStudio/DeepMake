TMP_DIR="$(mktemp -d)"
#make sure running with superuser privileges
if [ "$(id -u)" != "0" ]; then
    echo "Please run with sudo."
    exit 1
fi

#Define installation paths
user=`logname`
user_home=$(dscl . -read /Users/$user NFSHomeDirectory | awk '{print $2}')
config_path="$user_home/Library/Application Support/DeepMake"
install_path="/Library/Application Support/DeepMake"
conda_install_path="$user_home/miniconda3"
aeplugin_path="/Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore/"

mkdir -p $install_path
mkdir -p $config_path

#Create Config file
config_data='{ "Py_Environment": "conda activate deepmake;", "Startup_CMD": " python startup.py", "Directory": "cd '$install_path' ;" }' | sed 's^Application\ Support^Application\\\\\\\\\ Support^'
echo $config_data > $config_path/Config.json

#Install conda if not installed
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
if [ -z "$(ls -A "$install_path")" ]; then
    #Check if install_path is a git folder and if not remove it
    if ! [ -d "$install_path/.git" ]; then
        echo "Removing non-git folder at $install_path"
        rm -Rf "$install_path"
    fi
    echo "Installing DeepMake to $install_path"
    git clone https://github.com/DeepMakeStudio/DeepMake.git "$install_path"
else
    echo "Updating DeepMake at $install_path"
    cd "$install_path"
    git pull
    cd -
fi

#Create conda environment
$conda_path env create -y -f "$install_path"/environment.yml

#Install Diffusers plugin or update if already installed
if [ -z "$(ls -A "$install_path/plugin/Diffusers")" ]; then
    echo "Installing Diffusers to $install_path/plugin/Diffusers"
    git clone https://github.com/DeepMakeStudio/Diffusers.git "$install_path/plugin/Diffusers"
else
    echo "Updating Diffusers Plugin at $install_path/plugin/Diffusers"
    cd "$install_path/plugin/Diffusers"
    git pull
    cd -
fi

$conda_path env create -y -f "$install_path/plugin/Diffusers"/environment_mac.yml

#Download binaries
curl -s -L https://github.com/DeepMakeStudio/DeepMake/releases/latest/download/Binaries_Mac.zip -o "$TMP_DIR"/Binaries_Mac.zip

unzip -o "$TMP_DIR"/Binaries_Mac.zip -d "$TMP_DIR"
# if /DeepMake/DeepMake_ae.bundle exists, remove it
if [ -d "$aeplugin_path"/DeepMake_ae.bundle ]; then
    rm -Rf "$aeplugin_path"/DeepMake_ae.bundle
fi
cp -Rf "$TMP_DIR"/DeepMake/DeepMake_ae.bundle "$aeplugin_path"
# if /DeepMake/DeepMake_ae.bundle exists, remove it
if [ -d /Applications/appPrompt.app ]; then
    rm -Rf /Applications/appPrompt.app
fi
cp -Rf "$TMP_DIR"/DeepMake/appPrompt.app /Applications/appPrompt.app

rm -Rf $TMP_DIR

echo "Installation complete."