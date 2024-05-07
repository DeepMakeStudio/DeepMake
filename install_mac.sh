TMP_DIR="$(mktemp -d)"
if [ -z "$TMP_DIR" ]; then
    echo "Failed to create temporary directory"
    exit 1
fi
#make sure running with superuser privileges
if [ "$(id -u)" != "0" ]; then
    echo "Please run with sudo."
    exit 1
fi

#Define installation paths
user=`logname`
# if user is root, exit
if [ "$user" == "root" ]; then
    echo "User is root, please install using sudo in a user and not root account."
    exit 1
fi
if [ -z "$user" ]; then
    user=$SUDO_USER
fi
if [ -z "$user" ]; then
    echo "Failed to get user"
    exit 1
fi
user_home=$(dscl . -read /Users/$user NFSHomeDirectory | awk '{print $2}')
if [ -z "$user_home" ]; then
    user_home="/Users/$user"
fi
if [ -z "$user_home" ]; then
    echo "Failed to get user home"
    exit 1
fi
config_path="$user_home/Library/Application Support/DeepMake"
install_path="$user_home/Library/Application Support/DeepMake/DeepMake/"
conda_install_path="$user_home/miniconda3"
aeplugin_path="/Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore/"

#If config_path is inside / then exit
if [[ "$config_path" == /Library/* ]]; then
    echo "config_path is in root, exiting to prevent deletion of root files"
    echo $config_path
    exit 1
fi
if [[ "$install_path" == /Library/* ]]; then
    echo "install_path is in root, exiting to prevent deletion of root files"
    echo $install_path
    exit 1
fi

mkdir -p "$config_path"
if ! [ -d "$config_path" ]; then
    echo "Failed to create $config_path"
    exit 1
fi

mkdir -p "$install_path"
if ! [ -d "$install_path" ]; then
    echo "Failed to create $install_path"
    exit 1
fi


#Create Config file
config_data=`echo '{ "Py_Environment": "conda activate deepmake;", "Startup_CMD": " python startup.py", "Directory": "cd '$install_path' ;" }' | sed 's^Application\ Support^Application\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\ Support^'`
echo "$config_data" > "$config_path"/Config.json

#Install conda if not installed
if command -v conda &> /dev/null; then
    echo "conda is installed and available in the PATH"
    conda_path="conda"
    $conda_path init zsh bash
else
    conda_path=$conda_install_path"/bin/conda"
    echo "conda is not installed or not in the PATH"
    curl -s https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh -o $TMP_DIR/miniconda.sh
    bash $TMP_DIR/miniconda.sh -b -p $conda_install_path
    $conda_path init zsh bash
    $conda_path config --set auto_activate_base false
fi

if ! command -v conda &> /dev/null; then
    echo "conda is not installed or not in the PATH"
    exit 1
fi

#Install git from conda if not installed
if ! command -v git &> /dev/null; then
    $conda_path install -y git
fi

if ! command -v git &> /dev/null; then
    echo "git is not installed or not in the PATH"
    exit 1
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

if ! [ -d "$install_path" ]; then
    echo "Failed to install DeepMake to $install_path"
    exit 1
fi

#Create conda environment
$conda_path env update -f "$install_path"/environment.yml

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

if ! [ -d "$install_path/plugin/Diffusers" ]; then
    echo "Failed to install Diffusers Plugin to $install_path/plugin/Diffusers"
    exit 1
fi

$conda_path env update -f "$install_path/plugin/Diffusers"/environment_mac.yml

#Download binaries
curl -s -L --retry 10 --retry-delay 5 https://github.com/DeepMakeStudio/DeepMake/releases/latest/download/Binaries_Mac.zip -o "$TMP_DIR"/Binaries_Mac.zip
if ! [ -f "$TMP_DIR"/Binaries_Mac.zip ]; then
    echo "Failed to download Binaries_Mac.zip"
    exit 1
fi

if [ -z "$(ls -A "$TMP_DIR")" ]; then
    echo "Failed to download Binaries_Mac.zip"
    exit 1
fi

#if the plugin path does not exist, create it
if ! [ -d "$aeplugin_path" ]; then
    echo "Warning, $aeplugin_path does not exist, creating it (Did you install After Effects?)"
    mkdir -p "$aeplugin_path"
fi

#unzip and error if failed
unzip -o "$TMP_DIR"/Binaries_Mac.zip -d "$TMP_DIR" > /dev/null
if [ $? -ne 0 ]; then
    echo "Failed to unzip Binaries_Mac.zip"
    exit 1
fi

# if /DeepMake/DeepMake_ae.bundle exists, remove it
if [ -e "$aeplugin_path"/DeepMake_ae.bundle ]; then
    echo "Removing existing DeepMake_ae.bundle at $aeplugin_path"
fi
cp -Rf "$TMP_DIR"/DeepMake/DeepMake_ae.bundle "$aeplugin_path"

if [ ! -d "$aeplugin_path"/DeepMake_ae.bundle ]; then
    echo "Failed to install DeepMake_ae.bundle to $aeplugin_path"
    exit 1
fi

# if /Applications/appPrompt.app exists, remove it
if [ -e /Applications/appPrompt.app ]; then
    echo "Removing existing appPrompt.app at /Applications"
    rm -Rf /Applications/appPrompt.app
fi
cp -Rf "$TMP_DIR"/DeepMake/appPrompt.app /Applications/appPrompt.app

if [ ! -d /Applications/appPrompt.app ]; then
    echo "Failed to install appPrompt.app to /Applications"
    exit 1
fi

rm -Rf $TMP_DIR

#Change ownership of config_path and install_path
chown -R $user "$config_path"

#if ownership of config_path is not the user, exit
if [ "$(stat -f %Su "$config_path" | head -n1)" != "$user" ]; then
    echo "Failed to change ownership of $config_path to $user"
    echo "is $(stat -f %Su "$config_path") should be $user"
    exit 1
fi

chown -R $user "$install_path"

#if ownership of install_path is not the user, exit
if [ "$(stat -f %Su "$install_path" | head -n1)" != "$user" ]; then
    echo "Failed to change ownership of $install_path to $user"
    echo "is $(stat -f %Su "$install_path") should be $user"
    exit 1
fi

echo "Installation complete."