# DeepMake

DeepMake uses generative AI make content creation fast and easy. We leverage the leading open source AI to give you VFX in a few clicks, create stock video from text prompts, instantly segment layers, and more.

![Deepmake Logo](images/DeepMake.png)

# Support

For support see [DeepMake.com](https://deepmake.com/) or [![Join our Discord server](images/Discord.png)](https://discord.gg/Cy4zAXF8)

# DeepMake Backend

This repo contains the backend for DeepMake software.  It requires host plugins (Such as our After Effects plugin) as well as processing plugins (such as our Diffusers plugin for Text to Image generation)

# Installation

## Install the Deepmake Backend
* Clone this folder somewhere you can access it.
* Install Anaconda from [here](https://www.anaconda.com/download)
* From the DeepMake folder, 
    * Run "conda env create -f environment.yml"
## Install any processing plugins you want.
* go to the DeepMake folder
* cd to plugin
* git clone any processing plugins that you want to download (I.E. `git clone https://github.com/DeepMakeStudio/Diffusers`)
    * Win: Run `conda env create -f plugin/{folder}/environment.yml` for each package in the plugin folder.  (I.E. `conda env create -f plugin/Diffusers/environment.yml`)
    * Mac: Run `conda env create -f plugin/{folder}/environment_mac.yml` for each package in the plugin folder.  (I.E. `conda env create -f plugin/Diffusers/environment_mac.yml`)

## Install the Host plugins you desire:
* Windows
    * After Effects:
        * Download the [Binaries_Win.zip](https://github.com/DeepMakeStudio/DeepMake/releases/download/0.1.1-alpha/Binaries_Win.zip) file.
        * From that zip file
            * Install DeepMake_ae.aex to your After Effects plugin folder (`C:\Program Files\Adobe\Common\Plug-ins\7.0\MediaCore\`)
            * Install appPrompt.exe to the following folder (You may need to make the folder to put the file in) `C:\Program Files\DeepMake\Prompt\bin\appPrompt.exe`
    * Nuke: Coming Soon
* Mac:
    * After Effects:
        * Download the [Binaries_Mac.zip](https://github.com/DeepMakeStudio/DeepMake/releases/download/0.1.1-alpha/Binaries_Mac.zip) file.
        * From that zip file
            * Install DeepMake_ae.bundle to your After Effects plugin folder (`/Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore/`)
            * Install appPrompt.app to the following folder `/Applications/`
    * Nuke: Coming Soon

Congratulations!  You've installed DeepMake.  You can add new processing plugins as they become available.

# Usage

Now that you've completed installation you're ready to use DeepMake

First run the backend.

* Open an Anaconda Prompt in your DeepMake folder.
* run `conda activate deepmake`
* Run `python startup.py`
* Confirm the backend started successfully, then open the host plugin.

## After Effects

To use DeepMake simply activate the plugin from Effects/DeepMake/AI Plugin Renderer

Then you may choose from the installed plugins.  Each processing plugin will have it's own settings for you to configure.  DeepMake automatically makes the options that each processning plugin use visibile for you to modify.

## For more

For more information or if you want to get more help see [DeepMake.com](https://deepmake.com/) or join our [Discord server](https://discord.gg/Cy4zAXF8)

New Guides, Videos, and tutorials will be released over time.
