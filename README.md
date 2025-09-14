# lenovo-yoga-pro7-14IAH10-arch

(14 Sept 25)

Here is a quick compilation of issues I found when installing Arch on Lenovo Yoga Pro 7. Everything I need or tested so far is working well, but I'll be happy to update this MD.

**Disclaimer:** as far as I know, none of the steps described here pose any risk to the hardware.

**Disclaimer 2:** I've been a SW engineer for over a decade, have basic knowledge of Linux and have used it in the past for quite some time. I'm no sysadmin, though, and while I can read and understand how some systems work, I know fuck all about things like DSDT. On top of that, it's my first time installing and using Arch, so please excuse any mistakes I make, and feel free to correct me.

## What is working

Everything I tried so far.

- Dual boot with Windows 11 Pro (stock/OEM so far)
- WiFi connection works after sleep
- Audio volume issue solved / all speakers usable
- S3 sleep enabled
- [Power management profiles](https://wiki.archlinux.org/title/Lenovo_Yoga_7i#Power_management)
- Webcam
- Chrome reports hw graphics acceleration (haven't looked into it yet, glxinfo can't open display)

## What is not working / have not tested/setup

- Bluetooth (no systemctl service, so at least it does not seem to be working out of the box)


![](https://raw.githubusercontent.com/jfconde/lenovo-yoga-pro7-14IAH10-arch/refs/heads/main/images/screen_1.png)
![](https://raw.githubusercontent.com/jfconde/lenovo-yoga-pro7-14IAH10-arch/refs/heads/main/images/screen_2.png)
![](https://raw.githubusercontent.com/jfconde/lenovo-yoga-pro7-14IAH10-arch/refs/heads/main/images/screen_3.png)


## General instalation advice

Before doing anything, I set up Windows and installed all available firmware updates.

**Packages**

Although they are included in other steps, install `sof-firwmare`, `linux-firmware-cirrus`, `alsa-firmware` and `linux-firmware-intel`

**Grub screen resolution**

By default, if you use GRUB2, it will use the maximum display resolution, making the menu tiny, for ants.
Even though it's widely known, you can just use a lower resolution and re-generate grub config. 1600x1200
works quite well:

```
sudo echo "GRUB_GFXMODE=1600x1200" >> /etc/default/grub
grub-mkconfig -o /boot/grub/grub.cfg # Adjust if needed
```

## Problems / fixes

<details>
<summary>Wi-Fi not working after closing the lid (sleep)</summary>

**Note**: some posts online connect this to S3 sleep state being disabled (see its fix below). I tried after enabling S3 and the issue is still happening for me. Would love to learn more about this.

I installed the `networkmanager` package to manage my connections, alongside `iwd` to use as backend (described [here](https://wiki.archlinux.org/title/NetworkManager#Using_iwd_as_the_Wi-Fi_backend)). Whenever I reopened the lid, the Wi-Fi adapter would stop working. Using `ip link` I could see it as `DOWN` and trying to bring it up did not work, as I got a timeout writing to the Realtek device.

After trying many things, posts like [this](https://bbs.archlinux.org/viewtopic.php?id=307145) helped me. I had to unload those 3 modules (`iwlmld`, `iwlmvm`, `iwlwifi`). Some posts from other users and laptops would not include `iwlmvm`, but in my case it was necessary (`iwlwifi` couldn't be removed since it was being used by it).

#### Solution:

**Create a new script to execute by systemd when going to / resuming from sleep, and unload + reload WiFi modules.**

```
sudo touch /usr/lib/systemd/system-sleep/wifi-reload.sh
sudo chmod +X /usr/lib/systemd/system-sleep/wifi-reload.sh
```

Now edit the file (`wifi-reload.sh` in my case) and add the following to it:

```
#!/bin/sh

case $1/$2 in
        pre/*)
        modprobe -r iwlmvm iwlmld iwlwifi
        ;;
        post/*)
        modprobe iwlmvm iwlmld iwlwifi
        ;;
esac
```

After a reboot, the fix worked. I see with `ip link` that after every sleep there is a new interface (wlan1, wlan2, etc.) so the fix is probably not ideal, but works fine.

</details>

<details>
  <summary>Sound is very quiet / Only 2 out of 4 speakers work, no bass</summary>

It boils down to using the drivers in sof-firmware with the right device model in the driver.

**Solution:**

Follow [these steps](https://wiki.archlinux.org/title/Lenovo_Yoga_7i#Speaker_audio) and install the needed packages:

```
sudo pacman -S sof-firmware linux-firmware-cirrus alsa-firmware linux-firmware-intel
```

`linux-firmware-cirrus` is needed to manage the Cirrus amplifiers and DSPs of the audio device in the laptop, as I understood it. I'm not sure whether `linux-firmware-intel` is needed or not, but I installed it.

Tell the SOF firmware to use the right device configuration for our audio device. Do this by creating a new conf file with kernel module configuration. Create `/etc/modprobe.d/alc287_sof_model.conf` and add the following to it:

```
options snd_sof_intel_hda_generic hda_model=alc287-yoga9-bass-spk-pin
```

There are several suggestions using `snd_sof_intel_hda_common` and other option names instead. I think those are used in earlier versions of the kernel/package. After booting, you can use `sudo dmesg | grep -iE 'sof|snd'` to see if there are any kernel logs reporting a wrong/unrecognised sof option name, or if everything went well.

**Is it still not working?**

I spent a couple hours bashing my head against this, until I realised the `intel_hda` module was also present, and the kernel was picking it to manage the audio device, instead of the SOF ones. The symptom was that `wpctl status`, `alsamixer` and `cat /proc/asounc/cards` were showing a HDA Intel driver, not sof.

Solved by blacklisting the `snd_hda_intel` module. Create `/etc/modprobe.d/blacklist_snd_hda.conf` and add the following to it:

```
blacklist snd_hda_intel
```

Then reboot.
The previous commands should now return `sof-hda-dsp` and you should see new sliders for the amps in `alsamixer`.

</details>

<details>
<summary>No deep sleep, no option to enable S3 sleep state in BIOS</summary>

**IMPORTANT**: [you probably don't need this](https://wiki.archlinux.org/title/Power_management/Suspend_and_hibernate#Changing_suspend_method). I did it because I read in other posts that it could help both with the audio driver issues (somehow) or the wifi/sleep issues. Without their respective fixes, S3 didn't solve any of this, and those fixes don't need the S3 state at all.

Check the sleep states supported with `cat /sys/power/mem_sleep`:

`[s2idle]`

I tried every possible key combination I found to try to get to an "advanced BIOS" where I could enable S3, with no luck. I had to go the route suggested [here](https://wiki.archlinux.org/title/Lenovo_Yoga_7i#Activating_S3_sleep) and patch the DSDT used by Linux to manage laptop power settings (such as S3) using ACPI. I had never read the acronym DSDT before.

**The correct way (didn't work for me)**: you use `iasl` tools to dump and decompile the DSDT that is currently in use by your kernel. Then apply the [patch](https://wiki.archlinux.org/title/Lenovo_Yoga_7i#Activating_S3_sleep) here to the decompiled .dsl file. It's a change of 2 lines: one increasing the revision, and another replacing `Name (SS3, Zero)` with `Name (SS3, One)`. I didn't manage to do it: either decompiling the DSDT or decompiling it together with SSDT and neighbouring tables from `/sys/firmware/acpi/tables/` caused many errors, due to references being defined in multiple places. I was trying to wrap my head aroud this and try to solve this and update the code across the 29+ decompiled .dsl files. If someone can do it and/or point to how to solve those errors, I'd be happy to learn.

**Solution (not the best, but should be OK)**:

Install some ACPI tools (we need the decompiler) and decompile your DSDT. Do all of this in a folder of your choice, since we will generate some intermediate files.

```
sudo pacman -S acpica
```

Dump and decompile the DSDT:

```
sudo cat /sys/firmware/acpi/tables/DSDT > dsdt.dat
iasl -d dsdt.dat       # this generates dsdt.dsl
```

OK, this is where we deviate from the correct way. Take a look at the new file `dsdt.dsl`. This is where
you would apply the patch and then you would recompile it.
We only care about the first lines. Run `cat dsdt.dsl  | head -n20` and you should get something like this:

```
*
 * Intel ACPI Component Architecture
 * AML/ASL+ Disassembler version 20250404 (64-bit version)
 * Copyright (c) 2000 - 2025 Intel Corporation
 *
 * Disassembling to symbolic ASL+ operators
 *
 * Disassembly of dsdt.dat
 *
 * Original Table Header:
 *     Signature        "DSDT"
 *     Length           0x00084F6E (544622)
 *     Revision         0x02
 *     Checksum         0x5F  <-- Remember this!
 *     OEM ID           "INSYDE"
 *     OEM Table ID     "ARL"
 *     OEM Revision     0x00000002 (2) <-- We must set to 0x00000003
 *     Compiler ID      "ACPI"
 *     Compiler Version 0x00040000 (262144)
 */
```

What we are going to do is skip the decompilation and recompilation process entirely, and
use a hex editor to patch some bytes in the DSDT image/dump we have. I did this using `okteta`
which has a graphical interface. Use any hex editor of choice.

Note: values are in little-endian (0x1234 is stored as consecutive bytes `34 12`, not `12 34`)

```
sudo pacman -S okteta
```

Now, open okteta, and open the `dsdt.dat` file that we dumped in the first step.

If you want a summary of what we are going to do, here it is:
![](https://raw.githubusercontent.com/jfconde/lenovo-yoga-pro7-14IAH10-arch/refs/heads/main/images/screen_4.png)

The first 32 bytes should look like this in hexadecimal / char:

```
0x0000:  44 53 44 54 6E 4F 08 00 02 5F 49 4E 53 59 44 45
         D  S  D  T  n  O  .  .  .  ]  I  N  S  Y  D  E
         Signature   Length      Rv Cs OEM Id            (Rv=Revision, Cs=Checksum)

0x0010:  41 52 4C 00 00 00 00 00 02 00 00 00 41 43 50 49
         A  R  L  .  .  .  .  .  .  .  .  .  A  C  P  I
         OEM tabl                OEM Revisio Compiler ID
```

As you can see, the byte in position 0x0018 contains `02`, the least significant
byte of 0x0000002 (the OEM Revision). Let's increase it to `03`.

✏️ **Increase byte at position 0x0018 by 1 (`02` -> `03`)**

That's half of the patch! Now, you can use Ctrl+F to search for the Char sequence
`SS3`. In my case, the match is at offset 8FDF. You will know that it is the right
place if the match is surrounded by SS1, SS2 and SS4, and each of these strings is
followed by `SF` and `00`/`01`. For example, this is offset 8FD0-8FEF for me:

```
0x8FD0: 53 08 08 53 53 31 5F 00 08 53 53 32 5F 00 08 53
      S  .  .  S  S  1  _  .  .  S  S  2  _  .  .  S
0x8FE0: 53 33 5F 00 08 53 53 34 5F 01 5B 80 47 4E 56 53
      S  3  _  .  .  S  S  4  _  .  [  .  G  N  V  S
```

✏️ **Change the sequence `53 53 33 SF 00` (SSF3_0) to `53 53 33 SF 01` (SSF3_1)**

You could try to use this ACPI override now, but I already did that and spoiler alert:
it does not work. Do you remember the line ` *     Checksum         0x5D  <-- REMEMBER THIS`?
Well, these binary files or images contain a checksum that must be correct, or they
will not be accepted by the kernel. ChatGPT explains it better than me:

> The DSDT checksum is an 8-bit value stored in the ACPI Differentiated System Description Table (DSDT) header that ensures the table’s integrity. It’s calculated so that the sum of all bytes in the table, including the checksum field itself, equals zero modulo 256.

If you want a script to calculate and set the checksum byte correctly in python, here you go (made quickly with AI, but it works).

But in our case, we have the advantage that we know the previous checksum and we know
that we have increase the sum of all bytes by 2, because we incremented 2 different locations/bytes.
That means that ` the sum of all bytes in the table, including the checksum field itself` is now `2`, since
it was `0` before we incremented those 2 locations. Since the previous checksum was `5F`, in my case,
that means that I just need to update the checksum to be `5F-2 = 5D`.

✏️ **Decrease byte at position 0x0009 (checksum) by 2 (`5F` -> `5D`).**

✏️ **Save the file**

Cool! Now our `dsdt.dat` should contain the patch and have a valid checksum. To use it, we
will follow [these steps](https://wiki.archlinux.org/title/DSDT#Using_a_CPIO_archive).
Run them in the directory where you have `dsdt.dat`.

```
mkdir -p kernel/firmware/acpi
cp dsdt.aml kernel/firmware/acpi
find kernel | cpio -H newc --create > acpi_override
sudo cp acpi_override /boot
```

Finally, configure the boot loader to use the override. In my case, I am using Grub2, so I edited
`/etc/default/grub` and added the following line:

```
GRUB_EARLY_INITRD_LINUX_CUSTOM="acpi_override"
```

Then, as usual, time to re-create grub config:

```
grub-mkconfig -o /boot/grub/grub.cfg # Adjust if needed
```

Then you can see its usage: `sudo cat /boot/grub/grub.cfg | grep acpi_`:

> initrd /boot/intel-ucode.img /boot/acpi_override /boot/initramfs-linux.img
> initrd /boot/intel-ucode.img /boot/acpi_override /boot/initramfs-linux.img
> initrd /boot/intel-ucode.img /boot/acpi_override /boot/initramfs-linux-fallback.img

Reboot, and you should see S3 now enabled. `cat /sys/power/mem_sleep`:
`[s2idle] deep`

</details>
